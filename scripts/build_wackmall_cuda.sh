#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends git cmake ninja-build build-essential ca-certificates python3

commit=6aa17e3a3d25104a9c786abb76e920d32faaae10
git clone --filter=blob:none https://github.com/miltos22/llama-wackMall.git wackmall-source
git -C wackmall-source checkout --detach "$commit"
cmake -S wackmall-source -B wackmall-source/build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_CUDA_ARCHITECTURES=75-real \
  -DGGML_CUDA=ON -DGGML_CUDA_NO_VMM=ON -DGGML_BACKEND_DL=ON \
  -DGGML_NATIVE=OFF -DGGML_CPU_ALL_VARIANTS=ON \
  -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_BUILD_SERVER=ON \
  -DLLAMA_CURL=OFF -DLLAMA_OPENSSL=OFF
cmake --build wackmall-source/build --target llama-server --parallel 2
mkdir -p package dist
cp wackmall-source/build/bin/llama-server package/llama-server.bin
# Keep GGML plugins beside binary; preserve SONAME aliases when dereferencing.
find wackmall-source/build -name '*.so*' -exec cp -L '{}' package/ ';'
for name in libcudart libcublas libcublasLt; do
  find /usr/local/cuda/targets/x86_64-linux/lib -maxdepth 1 -name "$name.so*" -exec cp -L '{}' package/ ';'
done
test -s package/libggml-cuda.so
find package -maxdepth 1 -name 'libggml-cpu*.so' | grep -q .
LD_LIBRARY_PATH="$PWD/package" ldd package/llama-server.bin > package/linkage.txt
if grep -q 'not found' package/linkage.txt; then cat package/linkage.txt; exit 1; fi
cp wackmall-source/LICENSE package/LICENSE.llama-wackMall
printf '{"commit":"%s","cuda":"12.4","architecture":"sm_75","os":"ubuntu22.04"}\n' "$commit" > package/build-info.json
tar -czf dist/llama-wackmall-linux-cuda12.4-sm75.tar.gz -C package .
(cd dist && sha256sum llama-wackmall-linux-cuda12.4-sm75.tar.gz > llama-wackmall-linux-cuda12.4-sm75.tar.gz.sha256)
