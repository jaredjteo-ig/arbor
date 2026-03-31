# Arbor Build Toolkit
# Contains everything the partner needs to build Arbor images
# on a containerd-only Kubernetes cluster.
#
# Usage (partner runs with nerdctl or kubectl run):
#   nerdctl run -it --rm -v ~/.kube:/home/toolkit/.kube terrenefoundation/arbor-build-toolkit setup
#   nerdctl run -it --rm -v ~/.kube:/home/toolkit/.kube terrenefoundation/arbor-build-toolkit build backend v0.3.0
#
FROM alpine:3.20

# kubectl for creating K8s resources
RUN apk add --no-cache \
        bash \
        curl \
        ca-certificates \
    && ARCH="$(uname -m)" \
    && case "${ARCH}" in \
        x86_64)  KUBE_ARCH="amd64" ;; \
        aarch64) KUBE_ARCH="arm64" ;; \
        *)       echo "Unsupported arch: ${ARCH}" && exit 1 ;; \
       esac \
    && curl -fsSL "https://dl.k8s.io/release/$(curl -fsSL https://dl.k8s.io/release/stable.txt)/bin/linux/${KUBE_ARCH}/kubectl" \
        -o /usr/local/bin/kubectl \
    && chmod +x /usr/local/bin/kubectl \
    && kubectl version --client

# Non-root user
RUN adduser -D -h /home/toolkit toolkit
WORKDIR /home/toolkit/k8s-build

# Copy build system + app manifests
COPY manifests/ ./manifests/
COPY app-manifests/ ./app-manifests/
COPY setup.sh build.sh configure.sh deploy.sh entrypoint.sh ./
RUN chmod +x setup.sh build.sh configure.sh deploy.sh entrypoint.sh \
    && chown -R toolkit:toolkit /home/toolkit

USER toolkit
ENV HOME=/home/toolkit

ENTRYPOINT ["./entrypoint.sh"]
CMD ["help"]
