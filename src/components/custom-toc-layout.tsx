'use client'

import React, { createContext, useContext, useEffect, useRef, useState, forwardRef, type FC, type ReactNode, type ComponentProps, type FocusEventHandler, type MouseEventHandler } from 'react'
import { ThemeProvider } from 'next-themes'
import { SkipNavLink, Anchor, Button, Collapse } from 'nextra/components'
import { Search } from 'nextra/components'
import { ArrowRightIcon, ExpandIcon } from 'nextra/icons'
import { useFSRoute, useHash } from 'nextra/hooks'
import { normalizePages } from 'nextra/normalize-pages'
import type { PageMapItem, Heading } from 'nextra'
import type { Item, MenuItem, PageItem } from 'nextra/normalize-pages'
import cn from 'clsx'
import { usePathname } from 'next/navigation'
import NextLink from 'next/link'
import { DiscordIcon, GitHubIcon } from 'nextra/icons'
import scrollIntoView from 'scroll-into-view-if-needed'
import { CustomTocLayoutPropsSchema } from './schemas'

// Types
type NormalizePagesResult = ReturnType<typeof normalizePages>

// Contexts
const ConfigContext = createContext<NormalizePagesResult | null>(null)
const ThemeConfigContext = createContext<any>(null!)
const TOCContext = createContext<Heading[]>([])

// Hooks
function useConfig() {
  const normalizePagesResult = useContext(ConfigContext)
  if (!normalizePagesResult) {
    // Return default values for SSR
    return {
      normalizePagesResult: {
        activeThemeContext: { sidebar: true, navbar: true, footer: true, layout: 'default' },
        activeType: 'page',
        directories: [],
        docsDirectories: []
      },
      hideSidebar: false
    }
  }
  const { activeThemeContext, activeType } = normalizePagesResult
  return {
    normalizePagesResult,
    hideSidebar: !activeThemeContext.sidebar || activeType === 'page'
  }
}

function useThemeConfig() {
  const config = useContext(ThemeConfigContext)
  if (!config) {
    // Return default values for SSR
    return {
      sidebar: { defaultOpen: true, defaultMenuCollapseLevel: 2, toggleButton: true },
      toc: { title: 'On This Page', backToTop: 'Scroll to top', float: true },
      darkMode: true,
      themeSwitch: { dark: 'Dark', light: 'Light', system: 'System' },
      i18n: [],
      editLink: 'Edit this page',
      docsRepositoryBase: 'https://github.com/shuding/nextra',
      feedback: { content: 'Question? Give us feedback', labels: 'feedback' },
      search: null,
      lastUpdated: null,
      navigation: { next: true, prev: true }
    }
  }
  return config
}

function useTOC() {
  const toc = useContext(TOCContext)
  return toc || []
}

// Active anchor management
let activeSlug = ''
const listeners = new Set<() => void>()

function setActiveSlug(slug: string) {
  activeSlug = slug
  listeners.forEach(listener => listener())
}

function useActiveAnchor() {
  const [, rerender] = useState(activeSlug)
  useEffect(() => {
    const listener = () => rerender(activeSlug)
    listeners.add(listener)
    return () => {
      listeners.delete(listener)
    }
  }, [])
  return activeSlug
}

// Menu state management
let menu = false
const menuListeners = new Set<() => void>()

function setMenu(value: boolean) {
  menu = value
  menuListeners.forEach(listener => listener())
}

function useMenu() {
  const [, rerender] = useState(menu)
  useEffect(() => {
    const listener = () => rerender(menu)
    menuListeners.add(listener)
    return () => {
      menuListeners.delete(listener)
    }
  }, [])
  return menu
}

// Focused route management
let focusedRoute = ''
const focusedRouteListeners = new Set<() => void>()

function setFocusedRoute(route: string) {
  focusedRoute = route
  focusedRouteListeners.forEach(listener => listener())
}

function useFocusedRoute() {
  const [, rerender] = useState(focusedRoute)
  useEffect(() => {
    const listener = () => rerender(focusedRoute)
    focusedRouteListeners.add(listener)
    return () => {
      focusedRouteListeners.delete(listener)
    }
  }, [])
  return focusedRoute
}

// TOC Provider
function TOCProvider({ children, toc }: { children: ReactNode; toc: Heading[] }) {
  return <TOCContext.Provider value={toc}>{children}</TOCContext.Provider>
}

// Config Provider
function ConfigProvider({ children, pageMap, navbar, footer }: {
  children: ReactNode
  pageMap: PageMapItem[]
  navbar: ReactNode
  footer: ReactNode
}) {
  const [mounted, setMounted] = useState(false)
  const [pathname, setPathname] = useState('/')
  
  // Use useFSRoute outside of useEffect
  let currentPathname = '/'
  try {
    currentPathname = useFSRoute()
  } catch (error) {
    // Fallback to default route during SSR
    currentPathname = '/'
  }
  
  useEffect(() => {
    setMounted(true)
    setPathname(currentPathname)
  }, [currentPathname])

  // Use a default route during SSR
  const route = mounted ? pathname : '/'
  const normalizedPages = normalizePages({
    list: pageMap,
    route: route
  })
  const { activeThemeContext } = normalizedPages

  return (
    <ConfigContext.Provider value={normalizedPages}>
      {activeThemeContext.navbar && navbar}
      {children}
      {activeThemeContext.footer && footer}
    </ConfigContext.Provider>
  )
}

// Theme Config Provider
function ThemeConfigProvider(props: ComponentProps<typeof ThemeConfigContext.Provider>) {
  return React.createElement(ThemeConfigContext.Provider, props)
}

// Utility functions
function getGitIssueUrl({ labels, repository, title }: { labels: string; repository: string; title: string }) {
  const url = new URL(`${repository}/issues/new`)
  url.searchParams.set('title', title)
  url.searchParams.set('labels', labels)
  return url.toString()
}

function gitUrlParse(url: string) {
  return { href: url }
}

// Back to Top Component
function BackToTop({ className, hidden, children }: { className?: string; hidden?: boolean; children: ReactNode }) {
  const [show, setShow] = useState(false)

  useEffect(() => {
    const handleScroll = () => {
      setShow(window.scrollY > 100)
    }
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  if (hidden || !show) return null

  return (
    <button
      className={className}
      onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
    >
      {children}
    </button>
  )
}

// TOC Component
function TOC({ filePath, pageTitle }: { filePath: string; pageTitle: string }) {
  const activeSlug = useActiveAnchor()
  const tocRef = useRef<HTMLUListElement>(null)
  const themeConfig = useThemeConfig()
  const toc = useTOC()
  const hasMetaInfo =
    themeConfig.feedback?.content ||
    themeConfig.editLink ||
    themeConfig.toc?.extraContent ||
    themeConfig.toc?.backToTop

  const config = useConfig()
  const { activeType } = config.normalizePagesResult
  const anchors = themeConfig.toc?.float || activeType === 'page' ? toc : []

  const hasHeadings = anchors.length > 0
  const activeIndex = toc.findIndex(({ id }) => id === activeSlug)

  useEffect(() => {
    if (!activeSlug) return
    const anchor = tocRef.current?.querySelector(`a[href="#${activeSlug}"]`)
    if (!anchor) return

    scrollIntoView(anchor, {
      behavior: 'smooth',
      block: 'center',
      inline: 'center',
      scrollMode: 'if-needed',
      boundary: tocRef.current
    })
  }, [activeSlug])

  const feedbackLink =
    themeConfig.feedback?.link ??
    getGitIssueUrl({
      labels: themeConfig.feedback?.labels || 'feedback',
      repository: themeConfig.docsRepositoryBase || 'https://github.com/shuding/nextra',
      title: `Feedback for "${pageTitle}"`
    })

  const linkClassName = cn(
    'x:text-xs x:font-medium x:transition',
    'x:text-gray-600 x:dark:text-gray-400',
    'x:hover:text-gray-800 x:dark:hover:text-gray-200',
    'x:contrast-more:text-gray-700 x:contrast-more:dark:text-gray-100'
  )

  return (
    <div
      className={cn(
        'x:grid x:grid-rows-[min-content_1fr_min-content]',
        'x:sticky x:top-(--nextra-navbar-height) x:text-sm',
        'x:max-h-[calc(100vh-var(--nextra-navbar-height))]'
      )}
    >
      {hasHeadings && (
        <>
          <p className="x:pt-6 x:px-4 x:font-semibold x:tracking-tight">
            {themeConfig.toc?.title || 'On This Page'}
          </p>
          <ul
            ref={tocRef}
            className={cn(
              'x:p-4 nextra-scrollbar x:overscroll-y-contain x:overflow-y-auto x:hyphens-auto',
              'nextra-mask'
            )}
          >
            {anchors.map(({ id, value, depth }) => (
              <li className="x:my-2 x:scroll-my-6 x:scroll-py-6" key={id}>
                <a
                  href={`#${id}`}
                  className={cn(
                    'x:focus-visible:nextra-focus',
                    {
                      2: 'x:font-semibold',
                      3: 'x:ms-3',
                      4: 'x:ms-6',
                      5: 'x:ms-9',
                      6: 'x:ms-12'
                    }[depth],
                    'x:block x:transition-colors x:subpixel-antialiased',
                    id === activeSlug
                      ? 'x:text-primary-600 x:contrast-more:text-primary-600!'
                      : 'x:text-gray-600 x:hover:text-gray-900 x:dark:text-gray-400 x:dark:hover:text-gray-300',
                    'x:contrast-more:text-gray-900 x:contrast-more:underline x:contrast-more:dark:text-gray-50 x:break-words'
                  )}
                >
                  {value}
                </a>
              </li>
            ))}
          </ul>
        </>
      )}

      {hasMetaInfo && (
        <div
          className={cn(
            'x:grid x:gap-2 x:py-4 x:mx-4',
            hasHeadings && 'x:border-t nextra-border'
          )}
        >
          {themeConfig.feedback?.content && (
            <Anchor className={linkClassName} href={feedbackLink}>
              {themeConfig.feedback.content}
            </Anchor>
          )}

          {filePath && themeConfig.editLink && (
            <Anchor
              className={linkClassName}
              href={
                filePath.startsWith('http')
                  ? filePath
                  : `${gitUrlParse(themeConfig.docsRepositoryBase || 'https://github.com/shuding/nextra').href}/${filePath}`
              }
            >
              {themeConfig.editLink}
            </Anchor>
          )}

          {themeConfig.toc?.extraContent}

          {themeConfig.toc?.backToTop && (
            <BackToTop className={linkClassName} hidden={activeIndex < 2}>
              {themeConfig.toc.backToTop}
            </BackToTop>
          )}
        </div>
      )}
    </div>
  )
}

// Locale Switch Component
function LocaleSwitch({ lite, className }: { lite?: boolean; className?: string }) {
  const themeConfig = useThemeConfig()
  const hasI18n = themeConfig.i18n && themeConfig.i18n.length > 0
  
  if (!hasI18n) return null

  return (
    <div className={cn('x:flex x:items-center x:gap-2', className)}>
      <select className="x:bg-transparent x:border x:rounded x:px-2 x:py-1">
        {themeConfig.i18n?.map(({ locale, name }) => (
          <option key={locale} value={locale}>
            {name}
          </option>
        ))}
      </select>
    </div>
  )
}

// Theme Switch Component
function ThemeSwitch({ lite, className }: { lite?: boolean; className?: string }) {
  const themeConfig = useThemeConfig()
  
  if (!themeConfig.darkMode) return null

  return (
    <div className={cn('x:flex x:items-center x:gap-2', className)}>
      <button className="x:bg-transparent x:border x:rounded x:px-2 x:py-1">
        {themeConfig.themeSwitch?.light || 'Light'}
      </button>
      <button className="x:bg-transparent x:border x:rounded x:px-2 x:py-1">
        {themeConfig.themeSwitch?.dark || 'Dark'}
      </button>
    </div>
  )
}

// Navbar Component
interface NavbarProps {
  children?: ReactNode
  logoLink?: string | boolean
  logo: ReactNode
  projectLink?: string
  projectIcon?: ReactNode
  chatLink?: string
  chatIcon?: ReactNode
  className?: string
  align?: 'left' | 'right'
}

function Navbar({
  children,
  logoLink = true,
  logo,
  projectLink,
  projectIcon = <GitHubIcon height="24" aria-label="Project repository" />,
  chatLink,
  chatIcon = <DiscordIcon width="24" />,
  className,
  align = 'right'
}: NavbarProps) {
  const logoClass = cn(
    'x:flex x:items-center',
    align === 'left' ? 'x:max-md:me-auto' : 'x:me-auto'
  )
  return (
    <header
      className={cn(
        'nextra-navbar x:sticky x:top-0 x:z-30 x:w-full x:bg-transparent x:print:hidden',
        'x:max-md:[.nextra-banner:not([class$=hidden])~&]:top-(--nextra-banner-height)'
      )}
    >
      <div
        className={cn(
          'nextra-navbar-blur',
          'x:absolute x:-z-1 x:size-full',
          'nextra-border x:border-b',
          'x:backdrop-blur-md x:bg-nextra-bg/70'
        )}
      />
      <nav
        style={{ height: 'var(--nextra-navbar-height)' }}
        className={cn(
          'x:mx-auto x:flex x:max-w-(--nextra-content-width) x:items-center x:gap-4 x:pl-[max(env(safe-area-inset-left),1.5rem)] x:pr-[max(env(safe-area-inset-right),1.5rem)]',
          'x:justify-end',
          className
        )}
      >
        {logoLink ? (
          <NextLink
            href={typeof logoLink === 'string' ? logoLink : '/'}
            className={cn(
              logoClass,
              'x:transition-opacity x:focus-visible:nextra-focus x:hover:opacity-75'
            )}
            aria-label="Home page"
          >
            {logo}
          </NextLink>
        ) : (
          <div className={logoClass}>{logo}</div>
        )}
        <div className={align === 'left' ? 'x:me-auto' : ''}>
          {projectLink && <Anchor href={projectLink}>{projectIcon}</Anchor>}
          {chatLink && <Anchor href={chatLink}>{chatIcon}</Anchor>}
          {children}
        </div>
      </nav>
    </header>
  )
}

// Footer Component
function Footer({ className, children, ...props }: ComponentProps<'footer'>) {
  return (
    <div className="x:bg-gray-100 x:pb-[env(safe-area-inset-bottom)] x:dark:bg-neutral-900 x:print:bg-transparent">
      <div>
        <div className="x:mx-auto x:flex x:max-w-(--nextra-content-width) x:gap-2 x:py-2 x:px-4">
          <LocaleSwitch />
          <ThemeSwitch />
        </div>
      </div>
      <hr className="nextra-border" />
      {children && (
        <footer
          className={cn(
            'x:mx-auto x:flex x:max-w-(--nextra-content-width) x:justify-center x:py-12 x:text-gray-600 x:dark:text-gray-400 x:md:justify-start',
            'x:pl-[max(env(safe-area-inset-left),1.5rem)] x:pr-[max(env(safe-area-inset-right),1.5rem)]',
            className
          )}
          {...props}
        >
          {children}
        </footer>
      )}
    </div>
  )
}

// Sidebar Components
const TreeState: Record<string, boolean> = Object.create(null)

const classes = {
  link: cn(
    'x:flex x:rounded x:px-2 x:py-1.5 x:text-sm x:transition-colors x:[word-break:break-word]',
    'x:cursor-pointer x:contrast-more:border'
  ),
  inactive: cn(
    'x:text-gray-600 x:hover:bg-gray-100 x:hover:text-gray-900',
    'x:dark:text-neutral-400 x:dark:hover:bg-primary-100/5 x:dark:hover:text-gray-50',
    'x:contrast-more:text-gray-900 x:contrast-more:dark:text-gray-50',
    'x:contrast-more:border-transparent x:contrast-more:hover:border-gray-900 x:contrast-more:dark:hover:border-gray-50'
  ),
  active: cn(
    'x:bg-primary-100 x:font-semibold x:text-primary-800 x:dark:bg-primary-400/10 x:dark:text-primary-600',
    'x:contrast-more:border-primary-500!'
  ),
  list: cn('x:grid x:gap-1'),
  border: cn(
    'x:relative x:before:absolute x:before:inset-y-1',
    'x:before:w-px x:before:bg-gray-200 x:before:content-[""] x:dark:before:bg-neutral-800',
    'x:ps-3 x:before:start-0 x:pt-1 x:ms-3'
  ),
  wrapper: cn('x:p-4 x:overflow-y-auto nextra-scrollbar nextra-mask'),
  footer: cn(
    'nextra-sidebar-footer x:border-t nextra-border x:flex x:items-center x:gap-2 x:py-4 x:mx-4'
  )
}

type FolderProps = {
  item: PageItem | MenuItem | Item
  anchors: Heading[]
  onFocus: FocusEventHandler
  level: number
}

function Folder({ item: _item, anchors, onFocus, level }: FolderProps) {
  const routeOriginal = useFSRoute()
  const route = routeOriginal.split('#', 1)[0]!

  const item = {
    ..._item,
    children:
      _item.type === 'menu' ? getMenuChildren(_item as any) : _item.children
  }

  const hasRoute = !!item.route
  const active = hasRoute && [route, route + '/'].includes(item.route + '/')
  const activeRouteInside =
    active || (hasRoute && route.startsWith(item.route + '/'))

  const focusedRoute = useFocusedRoute()
  const focusedRouteInside = focusedRoute.startsWith(item.route + '/')

  const { theme } = item as Item
  const { defaultMenuCollapseLevel, autoCollapse } = useThemeConfig().sidebar || {}

  const open =
    TreeState[item.route] === undefined
      ? active ||
        activeRouteInside ||
        focusedRouteInside ||
        (theme && 'collapsed' in theme
          ? !theme.collapsed
          : level < (defaultMenuCollapseLevel || 2))
      : TreeState[item.route] || focusedRouteInside

  const [, rerender] = useState<object>()

  const handleClick: MouseEventHandler<
    HTMLAnchorElement | HTMLButtonElement
  > = event => {
    const el = event.currentTarget
    const isClickOnIcon =
      el !== event.target
    if (isClickOnIcon) {
      event.preventDefault()
    }
    const isOpen = el.parentElement!.classList.contains('open')
    const isLink = 'frontMatter' in item
    TreeState[item.route] = (isLink && !isClickOnIcon && !active) || !isOpen
    rerender({})
  }

  useEffect(() => {
    function updateTreeState() {
      if (activeRouteInside || focusedRouteInside) {
        TreeState[item.route] = true
      }
    }

    function updateAndPruneTreeState() {
      if (activeRouteInside && focusedRouteInside) {
        TreeState[item.route] = true
      } else {
        delete TreeState[item.route]
      }
    }

    if (autoCollapse) {
      updateAndPruneTreeState()
    } else {
      updateTreeState()
    }
  }, [activeRouteInside, focusedRouteInside, item.route, autoCollapse])

  const isLink = 'frontMatter' in item
  const ComponentToUse = isLink ? Anchor : Button

  return (
    <li className={cn({ open, active })}>
      <ComponentToUse
        {...(isLink
          ? { href: item.route, prefetch: false }
          : { 'data-href': item.route })}
        className={cn(
          'x:items-center x:justify-between x:gap-2',
          !isLink && 'x:text-start x:w-full',
          classes.link,
          active ? classes.active : classes.inactive
        )}
        onClick={handleClick}
        onFocus={onFocus}
      >
        {item.title}
        <ArrowRightIcon
          height="18"
          className={cn(
            'x:shrink-0',
            'x:rounded-sm x:p-0.5 x:hover:bg-gray-800/5 x:dark:hover:bg-gray-100/5',
            'x:motion-reduce:transition-none x:origin-center x:transition-all x:rtl:-rotate-180',
            open && 'x:ltr:rotate-90 x:rtl:-rotate-270'
          )}
        />
      </ComponentToUse>
      {item.children && (
        <Collapse isOpen={open}>
          <Menu
            className={classes.border}
            directories={item.children}
            anchors={anchors}
            level={level}
          />
        </Collapse>
      )}
    </li>
  )
}

function getMenuChildren(menu: MenuItem) {
  const routes = Object.fromEntries(
    (menu.children || []).map(route => [route.name, route])
  )
  return Object.entries(menu.items || {})
    .map(([key, item]) => ({
      ...(routes[key] || { name: key }),
      ...(item as object)
    }))
}

function Separator({ title }: { title: ReactNode }) {
  return (
    <li
      className={cn(
        '[word-break:break-word]',
        title
          ? 'x:not-first:mt-5 x:mb-2 x:px-2 x:py-1.5 x:text-sm x:font-semibold x:text-gray-900 x:dark:text-gray-100'
          : 'x:my-4'
      )}
    >
      {title || <hr className="x:mx-2 x:border-t nextra-border" />}
    </li>
  )
}

const handleClick = () => {
  setMenu(false)
}

function File({
  item,
  anchors,
  onFocus
}: {
  item: PageItem | Item
  anchors: Heading[]
  onFocus: FocusEventHandler
}) {
  const route = useFSRoute()
  const active = item.route && [route, route + '/'].includes(item.route + '/')
  const activeSlug = useActiveAnchor()

  if (item.type === 'separator') {
    return <Separator title={item.title} />
  }
  const href = (item as PageItem).href || item.route
  return (
    <li className={cn({ active })}>
      <Anchor
        href={href}
        className={cn(classes.link, active ? classes.active : classes.inactive)}
        onFocus={onFocus}
        prefetch={false}
      >
        {item.title}
      </Anchor>
      {active && anchors.length > 0 && (
        <ul className={cn(classes.list, classes.border)}>
          {anchors.map(({ id, value }) => (
            <li key={id}>
              <a
                href={`#${id}`}
                className={cn(
                  classes.link,
                  'x:focus-visible:nextra-focus x:flex x:gap-2 x:before:opacity-25 x:before:content-["#"]',
                  id === activeSlug ? classes.active : classes.inactive
                )}
                onClick={handleClick}
              >
                {value}
              </a>
            </li>
          ))}
        </ul>
      )}
    </li>
  )
}

interface MenuProps {
  directories: PageItem[] | Item[]
  anchors: Heading[]
  className?: string
  level: number
}

const handleFocus: FocusEventHandler<HTMLAnchorElement> = event => {
  const route =
    event.target.getAttribute('href') || event.target.dataset.href || ''
  setFocusedRoute(route)
}

const Menu = forwardRef<HTMLUListElement, MenuProps>(
  ({ directories, anchors, className, level }, forwardedRef) => (
    <ul className={cn(classes.list, className)} ref={forwardedRef}>
      {directories.map(item => {
        const ComponentToUse =
          item.type === 'menu' || item.children?.length ? Folder : File

        return (
          <ComponentToUse
            key={item.name}
            item={item}
            anchors={anchors}
            onFocus={handleFocus}
            level={level + 1}
          />
        )
      })}
    </ul>
  )
)
Menu.displayName = 'Menu'

function MobileNav() {
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  if (!mounted) {
    return null
  }

  const config = useConfig()
  const { directories } = config.normalizePagesResult
  const toc = useTOC()

  const menu = useMenu()
  const pathname = usePathname()
  const hash = useHash()

  useEffect(() => {
    setMenu(false)
  }, [pathname, hash])

  const anchors = toc.filter(v => v.depth === 2)
  const sidebarRef = useRef<HTMLUListElement>(null!)

  useEffect(() => {
    const sidebar = sidebarRef.current
    const activeLink = sidebar.querySelector('li.active')

    if (activeLink && menu) {
      scrollIntoView(activeLink, {
        block: 'center',
        inline: 'center',
        scrollMode: 'always',
        boundary: sidebar.parentNode as HTMLElement
      })
    }
  }, [menu])

  const themeConfig = useThemeConfig()
  const hasI18n = themeConfig.i18n && themeConfig.i18n.length > 0
  const hasMenu = themeConfig.darkMode || hasI18n

  return (
    <aside
      className={cn(
        'nextra-mobile-nav',
        'x:flex x:flex-col',
        'x:fixed x:inset-0 x:pt-(--nextra-navbar-height) x:z-20 x:overscroll-contain',
        'x:[contain:layout_style]',
        'x:md:hidden',
        'x:[.nextra-banner:not([class$=hidden])~&]:pt-[calc(var(--nextra-banner-height)+var(--nextra-navbar-height))]',
        'x:bg-nextra-bg',
        menu
          ? 'x:[transform:translate3d(0,0,0)]'
          : 'x:[transform:translate3d(0,-100%,0)]'
      )}
    >
      {themeConfig.search && (
        <div className="x:px-4 x:pt-4">{themeConfig.search}</div>
      )}
      <Menu
        ref={sidebarRef}
        className={classes.wrapper}
        directories={directories}
        anchors={anchors}
        level={0}
      />

      {hasMenu && (
        <div className={cn(classes.footer, 'x:mt-auto')}>
          <ThemeSwitch className="x:grow" />
          <LocaleSwitch className="x:grow x:justify-end" />
        </div>
      )}
    </aside>
  )
}

let lastScrollPosition = 0

const handleScrollEnd: ComponentProps<'div'>['onScrollEnd'] = event => {
  lastScrollPosition = event.currentTarget.scrollTop
}

function Sidebar() {
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  if (!mounted) {
    return null
  }

  const toc = useTOC()
  const config = useConfig()
  const { normalizePagesResult, hideSidebar } = config
  const themeConfig = useThemeConfig()
  const [isExpanded, setIsExpanded] = useState<boolean>(themeConfig.sidebar?.defaultOpen || true)
  const [showToggleAnimation, setToggleAnimation] = useState(false)
  const sidebarRef = useRef<HTMLDivElement>(null!)
  const sidebarControlsId = React.useId()

  const { docsDirectories, activeThemeContext } = normalizePagesResult
  const includePlaceholder = activeThemeContext.layout === 'default'

  useEffect(() => {
    if (window.innerWidth < 768) {
      return
    }
    const sidebar = sidebarRef.current

    if (lastScrollPosition) {
      sidebar.scrollTop = lastScrollPosition
      return
    }

    const activeLink = sidebar.querySelector('li.active')
    if (activeLink) {
      scrollIntoView(activeLink, {
        block: 'center',
        inline: 'center',
        scrollMode: 'always',
        boundary: sidebar.parentNode as HTMLDivElement
      })
    }
  }, [])

  const anchors =
    themeConfig.toc?.float ? [] : toc.filter(v => v.depth === 2)

  const hasI18n = themeConfig.i18n && themeConfig.i18n.length > 0
  const hasMenu =
    themeConfig.darkMode || hasI18n || themeConfig.sidebar?.toggleButton

  return (
    <>
      {includePlaceholder && hideSidebar && (
        <div className="x:max-xl:hidden x:h-0 x:w-64 x:shrink-0" />
      )}
      <aside
        id={sidebarControlsId}
        className={cn(
          'nextra-sidebar x:print:hidden',
          'x:transition-all x:ease-in-out',
          'x:max-md:hidden x:flex x:flex-col',
          'x:h-[calc(100dvh-var(--nextra-navbar-height))]',
          'x:top-(--nextra-navbar-height) x:shrink-0',
          isExpanded ? 'x:w-64' : 'x:w-20',
          hideSidebar ? 'x:hidden' : 'x:sticky'
        )}
      >
        <div
          className={cn(
            classes.wrapper,
            'x:grow',
            !isExpanded && 'no-scrollbar'
          )}
          ref={sidebarRef}
          onScrollEnd={handleScrollEnd}
        >
          {(!hideSidebar || !isExpanded) && (
            <Collapse isOpen={isExpanded} horizontal>
              <Menu
                directories={docsDirectories}
                anchors={anchors}
                level={0}
              />
            </Collapse>
          )}
        </div>
        {hasMenu && (
          <div
            className={cn(
              'x:sticky x:bottom-0 x:bg-nextra-bg',
              classes.footer,
              !isExpanded && 'x:flex-wrap x:justify-center',
              showToggleAnimation && [
                'x:*:opacity-0',
                isExpanded
                  ? 'x:*:animate-[fade-in_1s_ease_.2s_forwards]'
                  : 'x:*:animate-[fade-in2_1s_ease_.2s_forwards]'
              ]
            )}
          >
            <LocaleSwitch
              lite={!isExpanded}
              className={isExpanded ? 'x:grow' : ''}
            />
            <ThemeSwitch
              lite={!isExpanded || hasI18n}
              className={!isExpanded || hasI18n ? '' : 'x:grow'}
            />
            {themeConfig.sidebar?.toggleButton && (
              <Button
                aria-expanded={isExpanded}
                aria-controls={sidebarControlsId}
                title={isExpanded ? 'Collapse sidebar' : 'Expand sidebar'}
                className={({ hover }) =>
                  cn(
                    'x:rounded-md x:p-2',
                    hover
                      ? 'x:bg-gray-200 x:text-gray-900 x:dark:bg-primary-100/5 x:dark:text-gray-50'
                      : 'x:text-gray-600 x:dark:text-gray-400'
                  )
                }
                onClick={() => {
                  setIsExpanded(prev => !prev)
                  setToggleAnimation(true)
                }}
              >
                <ExpandIcon
                  height="12"
                  className={cn(
                    !isExpanded && 'x:*:first:origin-[35%] x:*:first:rotate-180'
                  )}
                />
              </Button>
            )}
          </div>
        )}
      </aside>
    </>
  )
}

// Main Layout Component
export default function CustomTocLayout(props: any) {
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  // Pre-process props to ensure all required properties are present
  const processedProps = {
    ...props,
    sidebar: {
      defaultMenuCollapseLevel: 2,
      defaultOpen: true,
      toggleButton: true,
      ...props.sidebar
    },
    toc: {
      title: 'On This Page',
      backToTop: 'Scroll to top',
      float: true,
      ...props.toc
    }
  }

  // Validate props using schema
  const validatedProps = CustomTocLayoutPropsSchema.parse(processedProps)
  
  const {
    children,
    banner,
    navbar,
    footer,
    editLink,
    docsRepositoryBase,
    feedback,
    sidebar,
    search,
    toc,
    darkMode,
    themeSwitch,
    i18n,
    lastUpdated,
    pageMap,
    navigation,
    nextThemes,
    ...rest
  } = validatedProps

  const themeConfig = {
    ...rest,
    editLink,
    docsRepositoryBase,
    feedback,
    sidebar,
    search,
    toc,
    darkMode,
    themeSwitch,
    i18n,
    lastUpdated,
    navigation: typeof navigation === 'boolean' ? { next: navigation, prev: navigation } : navigation
  }

  return (
    <ThemeConfigProvider value={themeConfig}>
      <ThemeProvider {...nextThemes}>
        <SkipNavLink />
        {banner}
        <ConfigProvider pageMap={pageMap} navbar={navbar} footer={footer}>
          <TOCProvider toc={[]}>
            {mounted ? (
              <>
                <MobileNav />
                <div className="x:flex x:min-h-[calc(100vh-var(--nextra-navbar-height))] x:max-md:flex-col">
                  <Sidebar />
                  <main className="x:flex x:min-w-0 x:flex-1 x:flex-col">
                    {children}
                  </main>
                  {toc?.float && (
                    <aside className="x:max-xl:hidden x:sticky x:top-(--nextra-navbar-height) x:z-10 x:h-[calc(100vh-var(--nextra-navbar-height))] x:w-64 x:shrink-0 x:overflow-y-auto x:py-6 x:pr-4">
                      <TOC filePath="" pageTitle="" />
                    </aside>
                  )}
                </div>
              </>
            ) : (
              <div className="x:flex x:min-h-[calc(100vh-var(--nextra-navbar-height))] x:max-md:flex-col">
                <main className="x:flex x:min-w-0 x:flex-1 x:flex-col">
                  {children}
                </main>
              </div>
            )}
          </TOCProvider>
        </ConfigProvider>
      </ThemeProvider>
    </ThemeConfigProvider>
  )
}