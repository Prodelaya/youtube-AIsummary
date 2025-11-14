#!/usr/bin/env python
"""
Script para medir throughput (requests/segundo) del sistema de caché.

Simula carga concurrente usando threading para medir cuántos requests
por segundo puede manejar el sistema con y sin caché.

Uso:
    poetry run python scripts/benchmark_throughput.py
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

# ==================== CONFIGURACIÓN ====================

API_BASE_URL = "http://localhost:8000/api/v1"
TOTAL_REQUESTS = 1000
CONCURRENT_WORKERS = 10
TIMEOUT = 5

# ==================== FUNCIONES ====================


def make_request(url: str, bypass_cache: bool = False) -> tuple[bool, float]:
    """
    Realiza un request HTTP GET.

    Args:
        url: URL del endpoint
        bypass_cache: Si True, envía header de bypass

    Returns:
        Tuple (success: bool, latency: float)
    """
    headers = {"X-Cache-Bypass": "true"} if bypass_cache else {}

    try:
        start = time.time()
        response = requests.get(url, headers=headers, timeout=TIMEOUT)
        latency = time.time() - start

        return (response.status_code == 200, latency)
    except Exception:
        return (False, 0.0)


def measure_throughput(url: str, bypass_cache: bool = False) -> dict:
    """
    Mide throughput con carga concurrente.

    Args:
        url: URL del endpoint
        bypass_cache: Si True, hace bypass del caché

    Returns:
        Dict con resultados (requests/seg, total_time, etc.)
    """
    print(f"  Ejecutando {TOTAL_REQUESTS} requests con {CONCURRENT_WORKERS} workers...", end=" ", flush=True)

    successful_requests = 0
    failed_requests = 0
    total_latency = 0.0

    start_time = time.time()

    # Ejecutar requests concurrentemente
    with ThreadPoolExecutor(max_workers=CONCURRENT_WORKERS) as executor:
        futures = [executor.submit(make_request, url, bypass_cache) for _ in range(TOTAL_REQUESTS)]

        for future in as_completed(futures):
            success, latency = future.result()
            if success:
                successful_requests += 1
                total_latency += latency
            else:
                failed_requests += 1

    total_time = time.time() - start_time

    # Calcular métricas
    requests_per_second = successful_requests / total_time if total_time > 0 else 0
    avg_latency = (total_latency / successful_requests * 1000) if successful_requests > 0 else 0

    print(f"✓ ({requests_per_second:.2f} req/s)")

    return {
        "total_requests": TOTAL_REQUESTS,
        "successful": successful_requests,
        "failed": failed_requests,
        "total_time": total_time,
        "requests_per_second": requests_per_second,
        "avg_latency_ms": avg_latency,
    }


# ==================== MAIN ====================


def main():
    """Ejecuta benchmark de throughput."""
    print("🚀 THROUGHPUT BENCHMARK")
    print(f"   API: {API_BASE_URL}")
    print(f"   Total requests: {TOTAL_REQUESTS}")
    print(f"   Concurrent workers: {CONCURRENT_WORKERS}")

    # Verificar servidor
    try:
        response = requests.get(f"{API_BASE_URL.replace('/api/v1', '')}/health", timeout=5)
        if response.status_code != 200:
            print("❌ Error: Servidor no está saludable")
            return
    except requests.exceptions.RequestException:
        print("❌ Error: No se puede conectar al servidor")
        return

    url = f"{API_BASE_URL}/stats"

    print("\n" + "=" * 60)
    print("THROUGHPUT: GET /stats")
    print("=" * 60)

    # Warmup
    print("\n🔥 Warming up cache...")
    requests.get(url, timeout=5)

    # 1. Con caché
    print("\n1️⃣  Throughput CON caché:")
    with_cache = measure_throughput(url, bypass_cache=False)

    # 2. Sin caché
    print("\n2️⃣  Throughput SIN caché (baseline):")
    without_cache = measure_throughput(url, bypass_cache=True)

    # Resumen
    print("\n" + "=" * 60)
    print("📊 RESULTADOS DE THROUGHPUT")
    print("=" * 60)

    print(f"\n✅ CON caché:")
    print(f"   Requests/segundo: {with_cache['requests_per_second']:.2f} req/s")
    print(f"   Tiempo total:     {with_cache['total_time']:.2f}s")
    print(f"   Latencia promedio: {with_cache['avg_latency_ms']:.2f}ms")
    print(f"   Exitosos/Total:   {with_cache['successful']}/{with_cache['total_requests']}")

    print(f"\n❌ SIN caché:")
    print(f"   Requests/segundo: {without_cache['requests_per_second']:.2f} req/s")
    print(f"   Tiempo total:     {without_cache['total_time']:.2f}s")
    print(f"   Latencia promedio: {without_cache['avg_latency_ms']:.2f}ms")
    print(f"   Exitosos/Total:   {without_cache['successful']}/{without_cache['total_requests']}")

    # Mejora
    improvement = (
        with_cache["requests_per_second"] / without_cache["requests_per_second"]
        if without_cache["requests_per_second"] > 0
        else 0
    )

    print(f"\n🚀 MEJORA:")
    print(f"   Throughput:  {improvement:.2f}x más rápido con caché")

    print("\n" + "=" * 60)
    print("✅ Benchmark completado")
    print("=" * 60)


if __name__ == "__main__":
    main()
