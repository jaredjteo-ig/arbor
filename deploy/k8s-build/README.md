# Arbor Build System for Kubernetes (No Docker Required)

Build Arbor container images directly on your Kubernetes cluster using [Kaniko](https://github.com/GoogleContainerTools/kaniko) — no Docker daemon needed. Works with containerd, CRI-O, or any OCI-compliant runtime.

**Your credentials never leave your cluster.**

---

## Prerequisites

| Requirement                                        | Why                                                |
| -------------------------------------------------- | -------------------------------------------------- |
| `kubectl` configured and connected to your cluster | Needed to create build jobs                        |
| Cluster admin or namespace-create permissions      | One-time setup creates the `arbor-build` namespace |
| A Docker Hub account                               | To push built images (or GHCR / private registry)  |
| A Docker Hub **Access Token**                      | Scoped credential — safer than your password       |
| Internet egress on port 443 from cluster           | Kaniko pulls base images and pushes to registry    |

### Create a Docker Hub Access Token

1. Log in to [hub.docker.com](https://hub.docker.com)
2. Go to **Account Settings > Security > Access Tokens**
3. Click **New Access Token**
4. Name: `arbor-build`
5. Permissions: **Read & Write**
6. Copy the token — you won't see it again

---

## Step 1: One-Time Setup

Clone this repo and run the setup script **on a machine with kubectl access to your cluster**:

```bash
cd deploy/k8s-build
chmod +x setup.sh build.sh
./setup.sh
```

The script will:

1. Create the `arbor-build` namespace with security policies
2. Ask which registry you use (Docker Hub, GHCR, or custom)
3. Prompt for your username and access token (read from keyboard, never visible)
4. Store credentials as a Kubernetes Secret in your cluster

**What gets created:**

| Resource                         | Purpose                                                               |
| -------------------------------- | --------------------------------------------------------------------- |
| Namespace `arbor-build`          | Isolated namespace for builds                                         |
| ServiceAccount `arbor-builder`   | Scoped permissions — can only run builds and read its own secret      |
| NetworkPolicy `build-pod-egress` | Build pods can only reach registries (port 443) — no lateral movement |
| ResourceQuota `build-limits`     | Limits total CPU/memory so builds can't starve your workloads         |
| Secret `registry-credentials`    | Your registry token — encrypted in etcd, never logged                 |

---

## Step 2: Build Images

### Build the backend

```bash
./build.sh backend v0.3.0
```

### Build the frontend

```bash
# Will prompt for your API URL
./build.sh frontend v0.3.0

# Or set it via environment variable
NEXT_PUBLIC_API_URL=https://arbor.example.com/api ./build.sh frontend v0.3.0
```

### Push to a different Docker Hub org

```bash
./build.sh backend v0.3.0 mycompany
# Pushes: mycompany/arbor-backend:v0.3.0
```

### Build from a specific branch or tag

```bash
GIT_REF=feat/my-branch ./build.sh backend v0.3.0
```

### What happens during a build

1. A Kubernetes Job is created in the `arbor-build` namespace
2. Kaniko pulls the Arbor source from GitHub (HTTPS, no SSH keys needed)
3. Kaniko builds the image using the existing Dockerfile
4. The image is pushed to your registry
5. Build logs are streamed to your terminal
6. The Job auto-deletes after 1 hour

---

## Step 3: Deploy

Once images are built, update your deployment to use them:

```yaml
# In your deployment manifest or docker-compose:
image: yourusername/arbor-backend:v0.3.0
image: yourusername/arbor-frontend:v0.3.0
```

If deploying to the same Kubernetes cluster, create an `imagePullSecret`:

```bash
# Re-use the same credentials for pulling
kubectl create secret docker-registry regcred \
    --namespace=your-app-namespace \
    --docker-server=https://index.docker.io/v1/ \
    --docker-username=YOUR_USERNAME \
    --docker-password=YOUR_TOKEN
```

Then reference it in your deployment:

```yaml
spec:
  imagePullSecrets:
    - name: regcred
```

---

## Security Model

| Concern                  | How it's handled                                             |
| ------------------------ | ------------------------------------------------------------ |
| **Credential storage**   | K8s Secret in etcd — never in files, env vars, or logs       |
| **Credential input**     | Read from stdin (not CLI args — args are visible in `/proc`) |
| **Privilege escalation** | Kaniko runs unprivileged — no Docker socket, no root         |
| **Network isolation**    | Build pods can only reach registries on port 443             |
| **Resource abuse**       | ResourceQuota caps CPU/memory across all builds              |
| **Input injection**      | All inputs validated against strict regex allowlists         |
| **Stale builds**         | Jobs auto-delete after 1 hour (`ttlSecondsAfterFinished`)    |
| **Supply chain**         | Kaniko executor image pinned by `@sha256:` digest            |
| **Re-run safety**        | Detects existing secrets; asks before regenerating passwords |
| **TLS**                  | Optional cert-manager integration; toggled via `configure`   |

---

## Troubleshooting

### Build pod stuck in Pending

```bash
kubectl describe job -n arbor-build -l app=arbor-kaniko-build
kubectl get events -n arbor-build --sort-by='.lastTimestamp'
```

Common causes:

- ResourceQuota exceeded (too many concurrent builds)
- Node doesn't have enough CPU/memory
- Kaniko image can't be pulled (check egress)

### Build fails with authentication error

```bash
# Verify secret exists and has data
kubectl get secret registry-credentials -n arbor-build -o jsonpath='{.data}' | head -c 50
```

If credentials are wrong, re-run `setup.sh` — it overwrites the existing secret.

### Build fails with Dockerfile error

The build uses the Dockerfiles in the Arbor repo (`deploy/Dockerfile.backend`, `deploy/Dockerfile.frontend`). Errors here are code issues, not build system issues. Check the Kaniko logs:

```bash
kubectl logs -n arbor-build -l app=arbor-kaniko-build --tail=50
```

### Clean up old build jobs

```bash
# List all build jobs
kubectl get jobs -n arbor-build

# Delete all completed jobs
kubectl delete jobs -n arbor-build -l app=arbor-kaniko-build
```

---

## Updating Credentials

If you need to rotate your Docker Hub token:

1. Create a new token on Docker Hub
2. Re-run `./setup.sh` — it will overwrite the existing secret
3. Old token can be revoked on Docker Hub

---

## Uninstalling

```bash
kubectl delete namespace arbor-build
```

This removes everything: the namespace, all secrets, all build jobs, all policies.
