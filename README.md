# QueryPie Community Edition

## 🧭 Before You Start
**QueryPie Community Edition** lets you experience the core features available in **QueryPie Enterprise**:
- Database Access Controller
- System Access Controller
- Kubernetes Access Controller
- Web Access Controller

**Important:** Community Edition supports **up to 5 user registrations** only.
*(If you need more than 5 users, please consider upgrading to the [Enterprise Plan](https://querypie.com/plans).)*

QueryPie runs as a typical web application and also includes proxy-based network server functionality.

---

## 🖥️ Server Requirements

### Minimum System Requirements
For basic testing and small deployments:

- **CPU:** 4 vCPUs (AMD64 Architecture)
- **Memory:** 16 GB RAM
- **Storage:** 100 GB+ disk space
- **OS:** Linux with Docker daemon

**Cloud Instances:**
- **AWS EC2:** `m6i.xlarge` or `m7i.xlarge`
- **GCP Compute Engine:** `c4-standard-4`, `n4-standard-4` (or any AMD64 -standard-4 models)

### Recommended for Production
For multi-user production environments:

- **CPU:** 8 vCPUs (AMD64 Architecture)  
- **Memory:** 32 GB RAM
- **Storage:** 100 GB+ disk space
- **OS:** Linux with Docker daemon

**Cloud Instances:**
- **AWS EC2:** `m6i.2xlarge` or `m7i.2xlarge`
- **GCP Compute Engine:** `c4-standard-8`, `n4-standard-8` (or any AMD64 -standard-8 models)

> 📄 For detailed requirements, see: [Prerequisites for Installation - Single Machine](https://querypie.atlassian.net/wiki/spaces/QCP/pages/865009675/Prerequisites+for+Installation+-+Single+Machine+EN)

---

## 🚀 Quick Installation

QueryPie installation is automated using Docker. Follow these simple steps:

### Step 1: Run Installation Command

Open your Linux server terminal and run this single command from your home directory:

```bash
bash <(curl https://dl.querypie.com/setup.v2.sh)
```

> ⏱️ **Installation time:** Typically 7-10 minutes

<p align="center">
  <img src="https://usqmjrvksjpvf0xi.public.blob.vercel-storage.com/main/public/documentation/install-guide-1-5WCes9Q5upf7mJGAWmsYJ6GozyUabS.png" alt="Installation started" style="max-width: 800px;" />
  <br/><em>Installation in progress</em>
</p>

### Step 2: Request License (During Installation)

While installation is running, apply for your free license:

1. Fill out the [license application form](https://querypie.com/querypie/license/community/apply)
2. A `.crt` license file will be sent to your email

### Step 3: Access QueryPie

Once installation completes, open QueryPie in your browser:

```
http://<your-server-ip>
or  
https://<your-server-ip>
```

> **Note:** Make sure your server IP is accessible from your computer

<p align="center">
  <img src="https://usqmjrvksjpvf0xi.public.blob.vercel-storage.com/main/public/documentation/install-guide-2-hL1Wh22qpC6A0R1bH2oqgynVRseIJn.png" alt="Installation complete" style="max-width: 800px;" />
  <br/><em>Installation completed successfully</em>
</p>

### Step 4: Upload License

Upload your `.crt` license file or copy-paste the PEM content:

<p align="center">
  <img src="https://usqmjrvksjpvf0xi.public.blob.vercel-storage.com/main/public/documentation/install-guide-3-jWNZ6jDvITcS1N3BlQdTSDmHNazbcV.png" alt="License upload" style="max-width: 800px;" />
  <br/><em>Enter license in PEM format</em>
</p>

### Step 5: First Login

Use the default admin credentials:

- **Username:** `qp-admin`
- **Password:** `querypie`

> 🔒 You'll be prompted to change the password on first login for security

<p align="center">
  <img src="https://usqmjrvksjpvf0xi.public.blob.vercel-storage.com/main/public/documentation/install-guide-4-XhGsdCCZPEq83mDGlaC1Iw0pzNRfpb.png" alt="Login screen" style="max-width: 800px;" />
  <br/><em>Initial login screen</em>
</p>

### Step 6: Setup Complete! 🎉

Congratulations! QueryPie is now ready to use.

<p align="center">
  <img src="https://usqmjrvksjpvf0xi.public.blob.vercel-storage.com/main/public/documentation/install-guide-5-droULybwgvRVIs1M01ibShv23WHEmL.png" alt="Welcome screen" style="max-width: 800px;" />
  <br/><em>Welcome to QueryPie!</em>
</p>

**Next Steps:**
- Check out the [Administrator Manual](https://docs.querypie.com/en/querypie-manual/11.0.0/-2) for environment setup
- Start configuring your database connections
- Invite team members (up to 5 users)

---

## 🔑 License Information

- **Requirement:** Valid license required after installation
- **Format:** Text file with `.crt` extension (PEM format)
- **Delivery:** Sent to your email address from application form
- **Duration:** Valid for one year from issue date
- **Usage:** Personal license, non-transferable

---

## 💬 Support & Community

Join our community for help and discussions:

🔗 [Official QueryPie Discord Channel](https://discord.com/invite/Cu39M55gMk)

Get support, ask questions, and share insights with other QueryPie users!
