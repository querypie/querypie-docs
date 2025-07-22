# QueryPie Community Edition Installation Guide

## 🧭 Before You Start
**QueryPie Community Edition** lets you experience the core features available in **QueryPie Enterprise**.
- Database Access Controller
- System Access Controller
- Kubernetes Access Controller
- Web Access Controller

However, the Community Edition supports **up to 5 user registrations**.
*(If you need to register more than 5 users, please consider upgrading to the [Enterprise Plan](https://querypie.com/plans)).*

QueryPie runs as a typical web application and also includes a proxy-based network server feature.

---

## 🖥️ Recommended Server Specifications

To ensure smooth installation and operation of QueryPie Community Edition, we recommend the following system environment:

**Type** | **Specifications**
-------- | ------------------
**Basic specifications** | - Hardware : CPU 4 vCPUs, AMD64 Architecture, Memory 16 GiB, Disk 100 GiB+<br/>- AWS EC2 : m6i.xlarge, m7i.xlarge<br/>- GCP Compute Engine : c4-standard-4, n4-standard-4 (or AMD64 architecture -standard-4 models)
**Recommended specifications for multi-user production environment** | - Hardware: CPU 8 vCPUs, AMD64 Architecture, Memory 32 GiB, Disk 100 GiB+<br/>- AWS EC2 : m6i.2xlarge, m7i.2xlarge<br/>- GCP Compute Engine : c4-standard-8, n4-standard-8 (or AMD64 architecture -standard-8 models)
**OS** | Linux (install and use docker daemon)

For detailed requirements, please refer to the document below:

📄 [Prerequisites for Installation - Single Machine (EN)](https://querypie.atlassian.net/wiki/spaces/QCP/pages/865009675/Prerequisites+for+Installation+-+Single+Machine+EN)

---

## 🐳 Installation Method
Installation is based on a Docker image and can be completed automatically with a single command.

### 1. Run the Command in the Terminal


After accessing your Linux server’s terminal, run the following command from your home directory:

```bash
bash <(curl https://dl.querypie.com/setup.v2.sh)
```

⏱️ Installation typically takes **7~10 minutes**.

<p align="center">
  <img src="https://usqmjrvksjpvf0xi.public.blob.vercel-storage.com/main/public/documentation/install-guide-1-5WCes9Q5upf7mJGAWmsYJ6GozyUabS.png" alt="Installation has started." style="max-width: 800px;" />
  <br/><em>Installation has started.</em>
</p>

<p align="center">
  <img src="https://usqmjrvksjpvf0xi.public.blob.vercel-storage.com/main/public/documentation/install-guide-2-hL1Wh22qpC6A0R1bH2oqgynVRseIJn.png" alt="Installation is complete." style="max-width: 800px;" />
  <br/><em>Installation is complete.</em>
</p>

### 2. Obtain a License During Installation

QueryPie Community Edition requires license registration.  
While installation is in progress, submit the [license application form](https://querypie.com/querypie/license/community/apply).  
A `.crt` text file will be sent to the email address you provided.

### 3. Access After Installation
Once installation is complete, access QueryPie in your browser at:

```
http://<server IP address>
or
https://<server IP address>
```

The IP address of the Linux server where QueryPie is installed must be accessible from the user’s PC.

### 4. Register the License

Upload the `.crt` file received by email, or copy and paste the PEM-formatted text content.

<p align="center">
  <img src="https://usqmjrvksjpvf0xi.public.blob.vercel-storage.com/main/public/documentation/install-guide-3-jWNZ6jDvITcS1N3BlQdTSDmHNazbcV.png" alt="Enter the license in PEM format." style="max-width: 800px;" />
  <br/><em>Enter the license in PEM format.</em>
</p>

### 5. Log In

Log in with the default account below.  
On your first login, you will be prompted to change your password for security.

- ID: `qp-admin`  
- Password: `querypie`

<p align="center">
  <img src="https://usqmjrvksjpvf0xi.public.blob.vercel-storage.com/main/public/documentation/install-guide-4-XhGsdCCZPEq83mDGlaC1Iw0pzNRfpb.png" alt="This is the initial login screen." style="max-width: 800px;" />
  <br/><em>This is the initial login screen.</em>
</p>

### 6. Installation Complete 🎉

Congratulations! Installation is complete.  
Refer to the [Administrator Manual](https://docs.querypie.com/en/querypie-manual/11.0.0/-2) to proceed with environment setup.

<p align="center">
  <img src="https://usqmjrvksjpvf0xi.public.blob.vercel-storage.com/main/public/documentation/install-guide-5-droULybwgvRVIs1M01ibShv23WHEmL.png" alt="Welcome to the initial login screen." style="max-width: 800px;" />
  <br/><em>Welcome to the initial login screen.</em>
</p>

---

## 🔑 About the License

- To use QueryPie, you must register a valid license after installation.  
- The license is provided as a text file with a `.crt` extension.  
- The license will be sent to the email address you entered when applying.  
- Each license is valid for one year from the date of issue.  
- The license is issued to the applicant personally and cannot be transferred to a third party.  

---

## 💬 Support & Inquiries
<!--
If you have any questions during the installation or use of QueryPie Community, you can contact us directly through the [QueryPie AI Hub](https://app.querypie.com/).  
Simply set up the **QueryPie Customer Center** preset on MCP by following the steps below to start chatting with support right from the chat window.

<p align="center">
  <img src="https://usqmjrvksjpvf0xi.public.blob.vercel-storage.com/main/public/documentation/install-guide-6-L6QPFwQviGkuqQZ85uBXJlzuszzOZm.png" alt="QueryPie Customer Center" style="max-width: 800px;" />
  <br/><em>QueryPie Customer Center</em>
</p>

1. Navigate to the Integration tab → Install QueryPie Customer Center.  
2. Go to the Preset tab → Click New Preset, then enter the following and click `Save Changes`:  
   - Name: Enter `QueryPie` (recommended).  
   - MCP Servers & Tools: Click `Select All`.  
3. Open the Chat tab → Select `@QueryPie` and enter your question.

You can also join our community on the [Official QueryPie Discord Channel](https://discord.gg/NsP98BHBm2) to ask questions and share insights with other users.
-->

Join our community on the [Official QueryPie Discord Channel](https://discord.com/invite/Cu39M55gMk) to ask questions and share insights with other users.
