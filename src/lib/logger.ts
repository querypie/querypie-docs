import {Logger as PinoLogger, pino} from 'pino';

// Define proper types for request, response, and error objects
interface LogRequest {
  method?: string;
  url?: string;
  headers?: Record<string, string | string[] | undefined>;
}

interface LogResponse {
  statusCode?: number;
  headers?: Record<string, string | string[] | undefined>;
}

interface LogError {
  type?: string;
  message?: string;
  stack?: string;
}

// Detect Vercel environment
const isVercel = process.env.VERCEL === '1';
const isProduction = process.env.NODE_ENV === 'production';
const isDevelopment = process.env.NODE_ENV === 'development';

// Helper function for log formatting in development environment
function formatLogForDevelopment(level: string, module: string, message: string, data?: Record<string, unknown>): string {
  const timestamp = new Date().toLocaleTimeString('ko-KR', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });

  const levelUpper = level.toUpperCase();

  let formattedLog = `[${timestamp}] ${levelUpper} (${module}): ${message}`;

  if (data && Object.keys(data).length > 0) {
    // Compress data to single line for output
    const dataStr = JSON.stringify(data).replace(/\s+/g, ' ');
    formattedLog += ` ${dataStr}`;
  }

  return formattedLog;
}

// Pino configuration optimized for Vercel environment
const logger = pino({
  // Log level configuration
  level: process.env.LOG_LEVEL || (isProduction ? 'info' : 'debug'),

  // Use basic JSON output in development environment
  transport: isDevelopment && !isVercel ? {
    target: 'pino-pretty',
    options: {
      colorize: true,
      translateTime: 'SYS:standard',
      ignore: 'pid,hostname',
      messageFormat: '[{time}] {level} ({module}/{service}): {msg}',
      levelFirst: true,
    }
  } : undefined,

  // Include Vercel environment information
  base: {
    env: process.env.NODE_ENV,
    vercel: isVercel,
    vercelEnv: process.env.VERCEL_ENV,
    vercelRegion: process.env.VERCEL_REGION,
    revision: process.env.VERCEL_GIT_COMMIT_SHA || 'unknown',
    deploymentId: process.env.VERCEL_DEPLOYMENT_ID,
  },

  // Timestamp format
  timestamp: () => `,"time":"${new Date().toISOString()}"`,

  // Recommended settings for Vercel
  serializers: {
    req: (req: LogRequest) => ({
      method: req.method,
      url: req.url,
      headers: req.headers,
    }),
    res: (res: LogResponse) => ({
      statusCode: res.statusCode,
      headers: res.headers,
    }),
    err: (err: LogError) => ({
      type: err.type,
      message: err.message,
      stack: err.stack,
    }),
  },

  // Log message format optimization
  messageKey: 'msg',

  // Performance optimization for Vercel environment
  ...(isVercel && {
    // Use sync flush in Vercel
    sync: false,
    // Log buffering optimization
    buffer: true,
  }),
});

// Define logger interface for better type safety
interface LoggerInterface {
  debug: (message: string, data?: Record<string, unknown>) => void;
  info: (message: string, data?: Record<string, unknown>) => void;
  warn: (message: string, data?: Record<string, unknown>) => void;
  error: (message: string, data?: Record<string, unknown>) => void;
}

// Custom logger wrapper for development environment
function createDevLogger(baseLogger: PinoLogger, module: string): LoggerInterface {
  return {
    debug: (message: string, data?: Record<string, unknown>) => {
      if (isDevelopment && !isVercel) {
        const formatted = formatLogForDevelopment('debug', module, message, data);
        console.log(formatted);
      } else {
        baseLogger.debug(data, message);
      }
    },
    info: (message: string, data?: Record<string, unknown>) => {
      if (isDevelopment && !isVercel) {
        const formatted = formatLogForDevelopment('info', module, message, data);
        console.log(formatted);
      } else {
        baseLogger.info(data, message);
      }
    },
    warn: (message: string, data?: Record<string, unknown>) => {
      if (isDevelopment && !isVercel) {
        const formatted = formatLogForDevelopment('warn', module, message, data);
        console.warn(formatted);
      } else {
        baseLogger.warn(data, message);
      }
    },
    error: (message: string, data?: Record<string, unknown>) => {
      if (isDevelopment && !isVercel) {
        const formatted = formatLogForDevelopment('error', module, message, data);
        console.error(formatted);
      } else {
        baseLogger.error(data, message);
      }
    },
  };
}

// Proxy-specific logger (includes Vercel environment information)
export const proxyLogger = createDevLogger(logger, 'proxy');

// Middleware-specific logger
export const middlewareLogger = createDevLogger(logger, 'middleware');

export default logger;
