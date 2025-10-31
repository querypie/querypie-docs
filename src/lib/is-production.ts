const isProduction = () => {
  // NOTE(JK): VERCEL_TARGET_ENV is the correct environment variable
  // to determine if the site is running in production or not.
  return process.env.VERCEL_TARGET_ENV === 'production';
};

export default isProduction;
