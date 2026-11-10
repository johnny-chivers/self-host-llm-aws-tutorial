# Test It Locally, Host It on AWS

Run a small open-source AI model on your laptop, prove it's good enough for a real job, then host the exact same model on Amazon Bedrock so your laptop is free and anyone with AWS access can use it.

Everything in this repo runs from one terminal.

---

## What the demo is

**The job: triage messy AWS support tickets.**

People write support tickets badly. Typos, capitals, missing details, three problems in one sentence. Before a ticket can be routed to the right team, someone has to read it and decide what it's about and how urgent it is.

We give that job to a small model. It reads the ticket and returns strict JSON:

**In:**
```
our lambda keeps timing out when it calls the RDS db, started after yesterdays deploy. checkout is completely down for ALL customers!!
```

**Out:**
```json
{
  "service": "Lambda",
  "severity": "critical",
  "category": "timeout",
  "summary": "Lambda times out calling RDS after deploy; checkout down"
}
```

Why this job:

- **It's narrow and repeatable.** A 1.5 billion parameter model can do it. You don't need a frontier model to classify a ticket.
- **The output is checkable.** Every answer is either valid JSON with the right values, or it isn't. No "vibes".
- **It's real.** The same pattern routes alerts, emails, and support queues in production systems.
- **Tickets can be sensitive.** Running the model yourself means you control where that text goes.

**How we score it:** `tickets.jsonl` has 20 tickets with the correct answer for each. `test_model.py` sends every ticket to the model and reports:

| Metric | Meaning |
|---|---|
| Pure JSON | The model returned only JSON, no markdown fences or chatter |
| Valid JSON | JSON could be extracted and parsed |
| Exact keys | Exactly `service`, `severity`, `category`, `summary` |
| Correct service / severity / category | Matches the expected answer |
| Latency | Warm response time (first call reported separately) |

We run the same test on the laptop and on AWS, so the move is proven, not claimed.

---

## Architecture

```
Laptop (test)                          AWS, eu-central-1 (host)
─────────────                          ────────────────────────
Ollama + qwen2.5:1.5b                  S3 bucket  ← model files from Hugging Face
      ▲                                    │
      │                                    ▼
test_model.py --target local           Bedrock Custom Model Import
test_model.py --target bedrock ──────► imported model (scales to zero when idle)
```

- **Model:** [Qwen 2.5 1.5B Instruct](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct), Apache 2.0, no access request needed
- **Locally:** Ollama runs a compressed (quantised) build of the model
- **On AWS:** Bedrock runs the original full weights from Hugging Face
- **API:** `InvokeModel` with the OpenAI chat format (the Converse API isn't supported for Qwen 2.5 imports)

---

## Amazon Bedrock and Custom Model Import

**Amazon Bedrock** is AWS's fully managed service for building with foundation models: one API, many models, and no servers or GPUs for you to run. It includes a catalog of ready-to-use models, Custom Model Import for your own models, and building blocks like Guardrails, Knowledge Bases and agents, all controlled with IAM like any other AWS service.

### Ways to run a model on AWS

| Option | You manage | You pay | Best for |
|---|---|---|---|
| Bedrock model catalog | Nothing | Per token | Standard models, fastest start |
| **Bedrock Custom Model Import** | **Your model files** | **Per CMU-minute, while active** | **A model you tested or fine-tuned** |
| SageMaker AI endpoints | Instances and scaling | Per instance-hour | Full control, always warm |
| EC2 or EKS (e.g. vLLM) | Everything | Per instance-hour | Custom serving stacks |

### How Custom Model Import works

1. **Store:** put the model weights in S3 in Hugging Face format (safetensors, `config.json`, tokenizer files).
2. **Import:** start an import job. Bedrock detects the model architecture.
3. **Host:** you get an imported model with its own ARN. No endpoints or instances to manage.
4. **Call:** use `InvokeModel`. You pay per Custom Model Unit per minute while it's active, and it scales to zero after 5 idle minutes.

Good to know:

- **Architectures:** Llama, Mistral, Mixtral, Qwen, GPT-OSS, Flan and GPTBigCode.
- **Limits:** text model weights under 200 GB; context length under 128K.
- **Regions:** eu-central-1, us-east-1, us-east-2, us-west-2. GPT-OSS imports are US East (N. Virginia) only.
- **Not supported:** batch inference and CloudFormation, which is why this repo uses CLI scripts.

See the [Custom Model Import documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/model-customization-import-model.html) for the current details — the supported architecture list grows over time.

> **On model choice:** this demo uses Qwen 2.5 1.5B because it's small, ungated and predictable. The steps are identical for any supported architecture. Note that "newer" doesn't always mean importable: Qwen3 is supported (disable its thinking mode for strict JSON), while Qwen3.5 uses a newer architecture class and transformers version than Custom Model Import currently targets.

---

## Repo layout

```
README.md                      you are here
common.py                      system prompt, JSON parser, scoring
tickets.jsonl                  20 test tickets with expected answers
demo_tickets.txt               tickets used on camera
test_model.py                  scoreboard: --target local | bedrock | both
requirements.txt
iam/                           policy templates used by setup_aws.sh
scripts/
  setup_aws.sh                 S3 bucket + IAM role for the import
  download_and_upload.sh       Hugging Face → S3
  import_model.sh              start import job and wait
  model_info.sh                model ARN + Custom Model Unit details
  teardown.sh                  delete everything in AWS
video/
  BRIEF.md                     one-page brief: what the video is, and the day's gotchas
  SCRIPT.md                    full video script
  DEMO-RUNBOOK.md              exact on-camera steps and pre-record checklist
  SLIDES.md                    slide list, in order
  slides.pdf                   the 22-slide deck, 1920x1080
  slides/                      each slide as standalone HTML
```

---

## Cost

- **Laptop:** free.
- **Import:** no charge to import.
- **Inference:** billed per Custom Model Unit (CMU) per minute while the model is active, in 5-minute windows. After 5 idle minutes it scales to zero and billing stops.
- **Storage:** a small monthly charge per CMU while the imported model exists.

A 1.5B model is small, so a follow-along session with bursts of testing is typically a few dollars. Check the **Custom Model Import** tab on the [Amazon Bedrock pricing page](https://aws.amazon.com/bedrock/pricing/) for current rates, and run `scripts/teardown.sh` when you're done.

---

## Prerequisites

| You need | Check |
|---|---|
| AWS account (a sandbox account with admin access is easiest) | You can sign in to the AWS console |
| AWS CLI v2, 2.32.0 or newer, signed in | `aws --version` and `aws sts get-caller-identity` |
| Python 3.10+ | `python3 --version` |
| git | `git --version` |
| Ollama | see [Installing Ollama](#installing-ollama) |
| ~6 GB free disk | model download plus Ollama model |

---

## Get the repo

### Install git and Python (if needed)

- **macOS:** `xcode-select --install` gives you git. Install Python from [python.org](https://www.python.org/downloads/) or with `brew install python`.
- **Windows:** install [Git for Windows](https://git-scm.com/download/win) and Python from [python.org](https://www.python.org/downloads/) (tick **Add python.exe to PATH**).
- **Linux:** use your package manager, for example `sudo apt install git python3 python3-venv`.

### Clone and install

```bash
git clone [REPO URL]
cd laptop-to-aws-llm

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

The virtual environment keeps this project's packages separate from the rest of your Python setup. Activate it (`source .venv/bin/activate`) in every new terminal you use for the demo.

---

## Set up the AWS CLI

### 1. Install or update the AWS CLI

Check what you have:

```bash
aws --version
```

You need **version 2**. Version **2.32.0 or newer** lets you sign in with `aws login`, the easiest option below. If you're on an older version, install again to update.

**macOS**

```bash
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
sudo installer -pkg AWSCLIV2.pkg -target /
```

Or download `AWSCLIV2.pkg` from the [AWS CLI install guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) and double-click it. Homebrew users can run `brew install awscli`.

**Windows**

```powershell
msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi
```

Or download and run the MSI installer from the install guide. Open a new terminal afterwards.

**Linux (x86_64)**

```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install          # add --update if the CLI is already installed
```

On ARM (for example Graviton or Raspberry Pi), use `awscli-exe-linux-aarch64.zip`.

### 2. Sign in

**Option A: `aws login` (recommended)**

Uses your normal AWS console sign-in, including MFA, and gives the CLI short-lived credentials that refresh automatically. No access keys stored on your machine.

```bash
aws login
```

Your browser opens. Choose your console session (or sign in), then return to the terminal. If prompted for a region, enter `eu-central-1`.

- If you sign in as an **IAM user or role**, it needs the **SignInLocalDevelopmentAccess** AWS managed policy.
- Requires AWS CLI 2.32.0 or newer.

**Option B: IAM Identity Center (company or AWS Organizations accounts)**

```bash
aws configure sso          # one-time setup, follow the prompts
aws sso login --profile <your-profile>
export AWS_PROFILE=<your-profile>
```

**Option C: access keys (not recommended)**

`aws configure` with an access key and secret. Only use this if A and B aren't available, and delete the keys when you're done.

### 3. Check it works

```bash
aws sts get-caller-identity
export AWS_REGION=eu-central-1
```

The first command shows the account and identity the CLI is using. The second sets Frankfurt for this terminal session; every script in this repo uses it.

### 4. Permissions

Your identity needs to:

- create an S3 bucket and upload objects
- create an IAM role and attach an inline policy (and pass it to Bedrock)
- create, read and delete Bedrock model import jobs and imported models
- call `bedrock:InvokeModel`

An administrator role in a sandbox account covers all of this.

### Troubleshooting

- **`Unable to locate credentials`:** run `aws login` (or `aws sso login`) again. Sessions expire.
- **Python can't find credentials but the CLI works:** update boto3 with `pip install -U boto3` so it supports your sign-in method, and check `AWS_PROFILE` is set in the same terminal if you use a named profile.
- **`aws: command not found` after installing:** open a new terminal.
- **Wrong account:** `aws sts get-caller-identity` shows which one you're using. Set `AWS_PROFILE` to switch.

---

## Installing Ollama

Ollama runs open-source models on your own machine and exposes them on a local API at `http://localhost:11434`.

### Hardware

| Machine | Qwen 2.5 1.5B |
|---|---|
| Apple Silicon Mac, 16 GB+ | Fast. This is the reference setup (M3 Pro, 18 GB) |
| Apple Silicon Mac, 8 GB | Works, close other apps |
| Windows/Linux with NVIDIA GPU | Fast |
| CPU-only laptop, 8 GB+ RAM | Works, slower |

The model download is about 1 GB. You don't need a GPU.

### macOS

**Option A: the app (recommended)**

1. Go to [ollama.com/download](https://ollama.com/download) and download the macOS version.
2. Open the downloaded file and drag **Ollama** into **Applications**.
3. Open Ollama from Applications. Approve the prompt to install the command line tool if asked.
4. A llama icon appears in the menu bar. Ollama is now running in the background.

**Option B: Homebrew**

```bash
brew install ollama
brew services start ollama        # runs Ollama in the background
```

### Windows

1. Go to [ollama.com/download](https://ollama.com/download) and download the Windows installer.
2. Run `OllamaSetup.exe` and follow the prompts.
3. Ollama starts automatically and runs in the system tray.
4. Use PowerShell or Windows Terminal for the commands below.

### Linux

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

The installer sets Ollama up as a background service on most distributions. If it isn't running, start it with `ollama serve` in a separate terminal.

### Check it's working

```bash
ollama --version
curl http://localhost:11434
```

The second command should print `Ollama is running`.

### Download and try the model

```bash
ollama pull qwen2.5:1.5b
ollama run qwen2.5:1.5b
```

`ollama run` opens a chat. Type a question, then `/bye` to exit.

### Commands you'll use in this demo

| Command | What it does |
|---|---|
| `ollama pull qwen2.5:1.5b` | Download the model |
| `ollama run qwen2.5:1.5b` | Chat with it in the terminal |
| `ollama ps` | Show loaded models and memory used |
| `ollama stop qwen2.5:1.5b` | Unload the model and free memory |
| `ollama list` | Show downloaded models |
| `ollama rm qwen2.5:1.5b` | Delete the model from disk |

### Troubleshooting

- **`connection refused` on port 11434:** Ollama isn't running. Open the app (macOS/Windows) or run `ollama serve`.
- **`address already in use`:** Ollama is already running, probably from the app. Don't start a second copy.
- **Slow responses:** close memory-heavy apps. On CPU-only machines, a few seconds per ticket is normal.
- **`model not found`:** run `ollama pull qwen2.5:1.5b` first.

---

## Step 1: Try the model locally

```bash
python test_model.py --target local \
  --ticket "our lambda keeps timing out calling RDS, checkout is down for everyone"
```

You should see JSON with `service`, `severity`, `category` and `summary`.

## Step 2: Score it locally

```bash
python test_model.py --target local
python test_model.py --target local --json-mode
```

`--json-mode` also asks the model to return a JSON object, which usually improves the "pure JSON" score. Add `--show` to print every raw answer.

---

## Step 3: Set up AWS

Make sure you're signed in (`aws sts get-caller-identity`) and your virtual environment is active, then:

```bash
export AWS_REGION=eu-central-1
./scripts/setup_aws.sh
```

Copy and run the three `export` lines it prints (`AWS_REGION`, `BUCKET`, `ROLE_ARN`).

## Step 4: Upload the model to S3

```bash
./scripts/download_and_upload.sh
```

This downloads the original model files from Hugging Face (about 3 GB) and syncs them to S3. Check the upload includes `model.safetensors`, `config.json`, `tokenizer.json` and `tokenizer_config.json`.

> Ollama and Bedrock use different packaging of the same model. Ollama runs a compressed GGUF file; Bedrock imports the original safetensors.

## Step 5: Import into Bedrock

```bash
./scripts/import_model.sh
```

The job usually takes several minutes. The script prints the status every 30 seconds until it's `Completed`.

**Console alternative:** Bedrock console (Frankfurt) → **Imported models** → **Import model** → name `ticket-triage-qwen` → S3 location `s3://<BUCKET>/qwen2.5-1.5b-instruct/` → **Create and use a new service role** → **Import model**.

If the job fails straight after creating the role, wait a minute and run the script again. New IAM roles take a moment to propagate.

## Step 6: Check model details and cost inputs

```bash
./scripts/model_info.sh
```

Note the Custom Model Units per copy and the CMU version, then run the `export BEDROCK_MODEL_ARN=...` line it prints.

## Step 7: Score it on AWS

```bash
python test_model.py --target bedrock --ticket "s3 costs doubled, low priority"
python test_model.py --target bedrock
python test_model.py --target both
```

Scores should be close to your laptop's. Small differences are expected: the laptop runs a compressed build, AWS runs the full weights.

## Step 8: See a cold start

After 5 minutes with no requests, Bedrock scales the model to zero. The next request restores it.

```bash
# Wait 5+ minutes, then:
python test_model.py --target bedrock --max-attempts 1 --ticket "dynamodb throttling in prod"
```

With one attempt you'll see `ModelNotReadyException`. Run it again without `--max-attempts 1`: the client retries with backoff until the model is back.

## Step 9: Offload from your laptop

```bash
ollama ps                              # model loaded, memory in use
ollama stop qwen2.5:1.5b               # free the memory
python test_model.py --target bedrock  # same test, nothing running locally
```

---

## Step 10: Tear down

```bash
./scripts/teardown.sh
```

Type `delete` to confirm. This removes the imported model, the S3 bucket and the IAM role. If you used the console to import, also delete the service role it created in the IAM console.

---

## When to use which

| Situation | Use |
|---|---|
| Trying a model, private, just you | **Your laptop** |
| A model you've tested that others or apps need to use | **Bedrock Custom Model Import** |
| A large, standard model | **Bedrock's managed model catalog** |
