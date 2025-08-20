const puppeteer = require('puppeteer');
const fs = require('fs');

class EnhancedWebsiteAnalyzer {
  constructor(baseUrl = null) {
    // 기본 URL을 동적으로 설정 (포트 3000 또는 3001)
    this.baseUrl = baseUrl || this.detectBaseUrl();
    this.visitedUrls = new Set();
    this.errorUrls = new Set();
    this.externalConnections = new Set();
    this.resourceErrors = new Set();
    this.analysisResults = {
      totalPages: 0,
      successfulPages: 0,
      errorPages: 0,
      resourceErrors: 0,
      externalConnections: 0,
      details: []
    };
    this.linkQueue = [];
    this.maxPages = 30; // 최대 30개 페이지까지 분석 (기본값)
  }

  detectBaseUrl() {
    // 환경 변수에서 포트 확인
    const port = process.env.PORT || '3000';
    return `http://localhost:${port}`;
  }

  async analyzeWebsite() {
    console.log('🌐 향상된 웹사이트 분석을 시작합니다...');
    console.log(`📡 대상 URL: ${this.baseUrl}/ko/querypie-manual`);
    
    const browser = await puppeteer.launch({
      headless: false,
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    try {
      const page = await browser.newPage();
      
      // Desktop mode 설정
      await this.setupDesktopMode(page);
      
      // 네트워크 요청 모니터링 설정
      await this.setupNetworkMonitoring(page);
      
      // 메인 페이지부터 시작
      await this.analyzePage(page, '/ko/querypie-manual');
      
      // 큐에 있는 링크들을 처리
      await this.processLinkQueue(page);
      
      // 결과 출력
      this.printResults();
      
    } catch (error) {
      console.error('❌ 분석 중 오류 발생:', error);
    } finally {
      await browser.close();
    }
  }

  async setupDesktopMode(page) {
    // Desktop user agent 설정
    await page.setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');
    
    // Desktop viewport 설정 (1920x1080)
    await page.setViewport({
      width: 1920,
      height: 1080,
      deviceScaleFactor: 1,
      isMobile: false,
      hasTouch: false,
      isLandscape: false
    });
    
    console.log('🖥️ Desktop mode로 설정되었습니다. (1920x1080)');
  }

  async setupNetworkMonitoring(page) {
    // 네트워크 요청 모니터링
    page.on('request', request => {
      const url = request.url();
      
      // docs.querypie.com으로의 직접 연결 검사
      if (url.includes('docs.querypie.com') && !url.includes('localhost:3000')) {
        this.externalConnections.add(url);
        console.log(`⚠️  외부 연결 감지: ${url}`);
      }
    });

    // 응답 모니터링
    page.on('response', response => {
      const url = response.url();
      const status = response.status();
      
      if (status === 404) {
        this.resourceErrors.add(url);
        console.log(`❌ 404 에러: ${url}`);
      }
    });
  }

  async analyzePage(page, path) {
    const fullUrl = `${this.baseUrl}${path}`;
    
    if (this.visitedUrls.has(fullUrl)) {
      return;
    }

    console.log(`\n📄 페이지 분석 중: ${fullUrl}`);
    this.visitedUrls.add(fullUrl);

    try {
      const response = await page.goto(fullUrl, { 
        waitUntil: 'networkidle2',
        timeout: 30000 
      });

      const status = response.status();
      
      if (status === 200) {
        this.analysisResults.successfulPages++;
        console.log(`✅ 성공: ${fullUrl}`);
        
        // 페이지 내 링크 수집 및 큐에 추가
        const links = await this.extractLinks(page);
        console.log(`🔗 발견된 링크 수: ${links.length}`);
        
        // 새로운 링크들을 큐에 추가
        this.addLinksToQueue(links);
        
        // 페이지 정보 저장
        this.analysisResults.details.push({
          url: fullUrl,
          status: status,
          links: links.length,
          title: await page.title(),
          timestamp: new Date().toISOString()
        });
        
      } else {
        this.analysisResults.errorPages++;
        this.errorUrls.add(fullUrl);
        console.log(`❌ 오류 (${status}): ${fullUrl}`);
      }

      this.analysisResults.totalPages++;

    } catch (error) {
      this.analysisResults.errorPages++;
      this.errorUrls.add(fullUrl);
      console.log(`❌ 페이지 로드 실패: ${fullUrl} - ${error.message}`);
    }
  }

  async extractLinks(page) {
    return await page.evaluate((baseUrl) => {
      const links = Array.from(document.querySelectorAll('a[href]'));
      return links.map(link => link.href).filter(href => 
        href.startsWith(baseUrl + '/ko/') && 
        !href.includes('#') &&
        !href.includes('javascript:') &&
        !href.includes('mailto:') &&
        !href.includes('tel:')
      );
    }, this.baseUrl);
  }

  addLinksToQueue(links) {
    for (const link of links) {
      if (!this.visitedUrls.has(link) && !this.linkQueue.includes(link)) {
        this.linkQueue.push(link);
      }
    }
  }

  async processLinkQueue(page) {
    console.log(`\n🔍 링크 큐 처리 중... (${this.linkQueue.length}개 링크 대기 중)`);
    
    while (this.linkQueue.length > 0 && this.analysisResults.totalPages < this.maxPages) {
      const link = this.linkQueue.shift();
      const url = new URL(link);
      const path = url.pathname;
      
      console.log(`\n📋 큐에서 처리 중: ${link} (남은 큐: ${this.linkQueue.length})`);
      await this.analyzePage(page, path);
      
      // 잠시 대기 (서버 부하 방지)
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
    
    if (this.analysisResults.totalPages >= this.maxPages) {
      console.log(`\n✅ 최대 페이지 수(${this.maxPages})에 도달했습니다.`);
    }
  }

  printResults() {
    console.log('\n' + '='.repeat(60));
    console.log('📊 향상된 웹사이트 분석 결과');
    console.log('='.repeat(60));
    
    console.log(`📄 총 분석 페이지: ${this.analysisResults.totalPages}`);
    console.log(`✅ 성공한 페이지: ${this.analysisResults.successfulPages}`);
    console.log(`❌ 오류 페이지: ${this.analysisResults.errorPages}`);
    console.log(`🔗 리소스 오류: ${this.resourceErrors.size}`);
    console.log(`🌐 외부 연결: ${this.externalConnections.size}`);
    console.log(`📋 남은 큐: ${this.linkQueue.length}`);
    
    if (this.resourceErrors.size > 0) {
      console.log('\n❌ 404 에러가 발생한 리소스들:');
      this.resourceErrors.forEach(url => {
        console.log(`  - ${url}`);
      });
    }
    
    if (this.externalConnections.size > 0) {
      console.log('\n⚠️ docs.querypie.com으로의 직접 연결:');
      this.externalConnections.forEach(url => {
        console.log(`  - ${url}`);
      });
    }
    
    console.log('\n📋 분석된 페이지 상세 정보:');
    this.analysisResults.details.forEach((detail, index) => {
      console.log(`${index + 1}. ${detail.title} (${detail.status})`);
      console.log(`   URL: ${detail.url}`);
      console.log(`   링크 수: ${detail.links}`);
      console.log(`   시간: ${detail.timestamp}`);
    });
    
    // 결과를 파일로 저장
    const report = {
      timestamp: new Date().toISOString(),
      summary: {
        totalPages: this.analysisResults.totalPages,
        successfulPages: this.analysisResults.successfulPages,
        errorPages: this.analysisResults.errorPages,
        resourceErrors: this.resourceErrors.size,
        externalConnections: this.externalConnections.size,
        remainingQueue: this.linkQueue.length
      },
      resourceErrors: Array.from(this.resourceErrors),
      externalConnections: Array.from(this.externalConnections),
      pageDetails: this.analysisResults.details,
      remainingLinks: this.linkQueue
    };
    
    // 결과 파일을 현재 디렉토리에 저장
    const outputPath = './enhanced_website_analysis_report.json';
    fs.writeFileSync(outputPath, JSON.stringify(report, null, 2));
    console.log(`\n💾 분석 결과가 ${outputPath} 파일로 저장되었습니다.`);
  }
}

// 분석 실행
async function main() {
  const analyzer = new EnhancedWebsiteAnalyzer();
  await analyzer.analyzeWebsite();
}

main().catch(console.error);
