// Simple logger implementation for Next.js proxy and other modules
// Uses console-based logging compatible with Edge runtime

// Environment detection
const isDevelopment = process.env.NODE_ENV === 'development';

// Logger interface for type safety
interface LoggerInterface {
  debug: (message: string, data?: Record<string, unknown>) => void;
  info: (message: string, data?: Record<string, unknown>) => void;
  warn: (message: string, data?: Record<string, unknown>) => void;
  error: (message: string, data?: Record<string, unknown>) => void;
}

// Format log message for development environment
function formatLogForDevelopment(
  level: string,
  module: string,
  message: string,
  data?: Record<string, unknown>,
): string {
  const timestamp = new Date().toLocaleTimeString('ko-KR', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });

  const levelUpper = level.toUpperCase();
  let formattedLog = `[${timestamp}] ${levelUpper} (${module}): ${message}`;

  if (data && Object.keys(data).length > 0) {
    // Compress data to a single line for readability
    const dataStr = JSON.stringify(data).replace(/\s+/g, ' ');
    formattedLog += ` ${dataStr}`;
  }

  return formattedLog;
}

// Create a logger instance for a specific module
// In development: uses console.log with formatted output
// In production: only warning and error logs are shown, debug and info are ignored
function createModuleLogger(module: string): LoggerInterface {
  // In development, use simple console logging with all levels
  if (isDevelopment) {
    return {
      debug: (message: string, data?: Record<string, unknown>) => {
        const formatted = formatLogForDevelopment('debug', module, message, data);
        console.log(formatted);
      },
      info: (message: string, data?: Record<string, unknown>) => {
        const formatted = formatLogForDevelopment('info', module, message, data);
        console.log(formatted);
      },
      warn: (message: string, data?: Record<string, unknown>) => {
        const formatted = formatLogForDevelopment('warn', module, message, data);
        console.warn(formatted);
      },
      error: (message: string, data?: Record<string, unknown>) => {
        const formatted = formatLogForDevelopment('error', module, message, data);
        console.error(formatted);
      },
    };
  }

  // In production, only log warning and error levels
  return {
    debug: (_message: string, _data?: Record<string, unknown>) => {
      // No-op in production
    },
    info: (_message: string, _data?: Record<string, unknown>) => {
      // No-op in production
    },
    warn: (message: string, data?: Record<string, unknown>) => {
      const formatted = formatLogForDevelopment('warn', module, message, data);
      console.warn(formatted);
    },
    error: (message: string, data?: Record<string, unknown>) => {
      const formatted = formatLogForDevelopment('error', module, message, data);
      console.error(formatted);
    },
  };
}

// Export createModuleLogger for use in other modules
export { createModuleLogger };

// Proxy-specific logger (renamed from middlewareLogger to reflect Next.js proxy naming)
export const proxyLogger = createModuleLogger('proxy');

// Default export for backward compatibility (if needed elsewhere)
export default createModuleLogger('app');
