import { Vercel } from '@vercel/sdk';
import dotenv from 'dotenv';

dotenv.config({ path: '.env' });

const vercel = new Vercel({
  bearerToken: process.env.VERCEL_TOKEN,
});

const teamId = process.env.VERCEL_TEAM_ID;
const targetEnv = process.env.TARGET_ENV;
const branch = process.env.BRANCH;

const POLL_INTERVAL_MS = 5_000;
const POLL_TIMEOUT_MS = 10 * 60 * 1_000; // 10 minutes
const MAX_RETRIES = 2;
const RETRY_DELAY_MS = 15_000;

/** Statuses that indicate deployment is still in progress */
const IN_PROGRESS_STATUSES = new Set([
  'QUEUED',
  'INITIALIZING',
  'ANALYZING',
  'BUILDING',
  'DEPLOYING',
]);

async function createDeployment() {
  const target = targetEnv === 'preview' ? undefined : targetEnv;
  return vercel.deployments.createDeployment({
    teamId,
    requestBody: {
      name: 'querypie-docs',
      target,
      gitSource: {
        type: 'github',
        repo: 'querypie-docs',
        ref: branch,
        org: 'querypie',
      },
    },
  });
}

async function pollDeployment(deploymentId) {
  const startTime = Date.now();

  while (true) {
    await new Promise(resolve => setTimeout(resolve, POLL_INTERVAL_MS));

    if (Date.now() - startTime > POLL_TIMEOUT_MS) {
      throw new Error(`Deployment polling timed out after ${POLL_TIMEOUT_MS / 1_000}s`);
    }

    let statusResponse;
    try {
      statusResponse = await vercel.deployments.getDeployment({
        idOrUrl: deploymentId,
        withGitRepoInfo: 'true',
      });
    } catch (error) {
      if (error.statusCode === 404) {
        const err = new Error(
          'Deployment was removed (HTTP 404). ' +
          'This typically happens when Vercel auto-cancels a deployment ' +
          'because a newer one was triggered for the same branch.',
        );
        err.cancelled = true;
        throw err;
      }
      throw error;
    }

    const { status, url } = statusResponse;
    console.log(`Deployment status: ${status}`);

    if (IN_PROGRESS_STATUSES.has(status)) {
      continue;
    }

    if (status === 'READY') {
      return url;
    }

    // CANCELED, ERROR, or any other terminal status
    const err = new Error(`Deployment ended with status: ${status}`);
    err.cancelled = status === 'CANCELED';
    throw err;
  }
}

async function createAndCheckDeployment() {
  console.log(`Creating deployment: target=[${targetEnv}], branch=[${branch}]`);

  const createResponse = await createDeployment();
  console.log(`Deployment created: ID ${createResponse.id}, status ${createResponse.status}`);

  const url = await pollDeployment(createResponse.id);
  console.log(`Deployment successful: ${url}`);
}

(async () => {
  for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
    try {
      await createAndCheckDeployment();
      return;
    } catch (error) {
      if (error.cancelled && attempt < MAX_RETRIES) {
        console.log(
          `Attempt ${attempt}/${MAX_RETRIES} failed: ${error.message}\n` +
          `Retrying in ${RETRY_DELAY_MS / 1_000}s...`,
        );
        await new Promise(resolve => setTimeout(resolve, RETRY_DELAY_MS));
        continue;
      }

      console.error(`Error: ${error.message}`);
      process.exit(1);
    }
  }
})();
