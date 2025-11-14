#!/usr/bin/env python
"""
Script de benchmarking para el sistema de caché de estadísticas.

Este script mide:
1. Latencia de endpoints con y sin caché
2. Cache hit rate bajo carga
3. Throughput (requests/segundo)
4. Comparativa de rendimiento

Uso:
    poetry run python scripts/benchmark_cache.py

Requisitos:
    - Servidor FastAPI corriendo en http://localhost:8000
    - Redis corriendo y accesible
    - Base de datos con al menos una fuente
"""

import statistics
import time
from typing import Any

import requests

# ==================== CONFIGURACIÓN ====================

API_BASE_URL = "http://localhost:8000/api/v1"
WARMUP_REQUESTS = 5
BENCHMARK_REQUESTS = 100
MIXED_LOAD_REQUESTS = 1000

# IDs de fuentes de ejemplo (obtener dinámicamente o hardcodear)
SOURCE_IDS = []

# ==================== UTILIDADES ====================


def measure_latency(url: str, bypass_cache: bool = False, iterations: int = 100) -> dict[str, Any]:
    """
    Mide latencia de un endpoint con múltiples requests.

    Args:
        url: URL del endpoint a medir
        bypass_cache: Si True, envía header X-Cache-Bypass
        iterations: Número de requests a realizar

    Returns:
        Dict con estadísticas: p50, p95, p99, avg, min, max
    """
    headers = {"X-Cache-Bypass": "true"} if bypass_cache else {}
    latencies = []

    print(f"  Midiendo latencia ({iterations} requests)...", end=" ", flush=True)

    for _ in range(iterations):
        start = time.time()
        response = requests.get(url, headers=headers, timeout=5)
        latency = (time.time() - start) * 1000  # ms

        if response.status_code == 200:
            latencies.append(latency)

    # Calcular estadísticas
    latencies.sort()
    result = {
        "count": len(latencies),
        "avg": statistics.mean(latencies),
        "median": statistics.median(latencies),
        "p50": latencies[int(len(latencies) * 0.50)],
        "p95": latencies[int(len(latencies) * 0.95)],
        "p99": latencies[int(len(latencies) * 0.99)],
        "min": min(latencies),
        "max": max(latencies),
    }

    print(f"✓ (avg: {result['avg']:.2f}ms)")
    return result


def measure_cache_hit_rate(url: str, total_requests: int = 1000) -> dict[str, Any]:
    """
    Mide el cache hit rate con carga mixta.

    Simula tráfico real con requests repetidos y nuevos.

    Args:
        url: URL base del endpoint
        total_requests: Total de requests a realizar

    Returns:
        Dict con hits, misses, hit_rate
    """
    print(f"  Midiendo cache hit rate ({total_requests} requests)...", end=" ", flush=True)

    hits = 0
    misses = 0

    for i in range(total_requests):
        # 70% requests a mismo endpoint (cache hit esperado)
        # 30% requests con bypass (cache miss)
        if i % 10 < 7:
            # Request normal (debería ser cache hit después del primero)
            response = requests.get(url, timeout=5)
        else:
            # Request con bypass
            response = requests.get(url, headers={"X-Cache-Bypass": "true"}, timeout=5)

        if response.status_code == 200:
            cache_status = response.headers.get("X-Cache-Status", "UNKNOWN")
            if cache_status == "HIT":
                hits += 1
            elif cache_status == "MISS":
                misses += 1

    total = hits + misses
    hit_rate = (hits / total * 100) if total > 0 else 0

    print(f"✓ (hit rate: {hit_rate:.1f}%)")

    return {"hits": hits, "misses": misses, "total": total, "hit_rate": hit_rate}


def warm_up_cache(url: str, iterations: int = 5) -> None:
    """
    Precalienta el caché con requests iniciales.

    Args:
        url: URL del endpoint
        iterations: Número de requests de warmup
    """
    print(f"  Warming up cache ({iterations} requests)...", end=" ", flush=True)
    for _ in range(iterations):
        requests.get(url, timeout=5)
    print("✓")


def clear_cache(url: str) -> None:
    """
    Limpia el caché usando header de bypass.

    Args:
        url: URL del endpoint
    """
    print("  Clearing cache...", end=" ", flush=True)
    requests.get(url, headers={"X-Cache-Bypass": "true"}, timeout=5)
    print("✓")


# ==================== BENCHMARKS ====================


def benchmark_global_stats() -> dict[str, Any]:
    """
    Benchmark del endpoint GET /stats (estadísticas globales).

    Returns:
        Dict con resultados de benchmarks
    """
    print("\n" + "=" * 60)
    print("BENCHMARK 1: GET /stats (Global Statistics)")
    print("=" * 60)

    url = f"{API_BASE_URL}/stats"
    results = {}

    # 1. Baseline: Sin caché (bypass siempre)
    print("\n1️⃣  Latencia SIN caché (baseline):")
    clear_cache(url)
    results["without_cache"] = measure_latency(url, bypass_cache=True, iterations=BENCHMARK_REQUESTS)

    # 2. Con caché (warmup + medición)
    print("\n2️⃣  Latencia CON caché:")
    clear_cache(url)
    warm_up_cache(url, WARMUP_REQUESTS)
    results["with_cache"] = measure_latency(url, bypass_cache=False, iterations=BENCHMARK_REQUESTS)

    # 3. Cache hit rate bajo carga
    print("\n3️⃣  Cache hit rate bajo carga mixta:")
    clear_cache(url)
    warm_up_cache(url, 1)
    results["hit_rate"] = measure_cache_hit_rate(url, MIXED_LOAD_REQUESTS)

    # 4. Calcular mejora
    improvement = (
        results["without_cache"]["avg"] / results["with_cache"]["avg"]
        if results["with_cache"]["avg"] > 0
        else 0
    )
    results["improvement_factor"] = improvement

    return results


def benchmark_source_stats(source_id: str) -> dict[str, Any]:
    """
    Benchmark del endpoint GET /stats/sources/{id}.

    Args:
        source_id: UUID de la fuente a benchmarkear

    Returns:
        Dict con resultados de benchmarks
    """
    print("\n" + "=" * 60)
    print(f"BENCHMARK 2: GET /stats/sources/{{id}} (Source: {source_id[:8]}...)")
    print("=" * 60)

    url = f"{API_BASE_URL}/stats/sources/{source_id}"
    results = {}

    # 1. Baseline: Sin caché
    print("\n1️⃣  Latencia SIN caché (baseline):")
    clear_cache(url)
    results["without_cache"] = measure_latency(url, bypass_cache=True, iterations=BENCHMARK_REQUESTS)

    # 2. Con caché
    print("\n2️⃣  Latencia CON caché:")
    clear_cache(url)
    warm_up_cache(url, WARMUP_REQUESTS)
    results["with_cache"] = measure_latency(url, bypass_cache=False, iterations=BENCHMARK_REQUESTS)

    # 3. Cache hit rate
    print("\n3️⃣  Cache hit rate bajo carga mixta:")
    clear_cache(url)
    warm_up_cache(url, 1)
    results["hit_rate"] = measure_cache_hit_rate(url, MIXED_LOAD_REQUESTS)

    # 4. Mejora
    improvement = (
        results["without_cache"]["avg"] / results["with_cache"]["avg"]
        if results["with_cache"]["avg"] > 0
        else 0
    )
    results["improvement_factor"] = improvement

    return results


def print_summary(global_results: dict, source_results: dict | None = None) -> None:
    """
    Imprime resumen de resultados de benchmarks.

    Args:
        global_results: Resultados de /stats
        source_results: Resultados de /stats/sources/{id} (opcional)
    """
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE RESULTADOS")
    print("=" * 60)

    # Global Stats
    print("\n🌍 GET /stats (Global Statistics):")
    print(f"   Sin caché:  {global_results['without_cache']['avg']:.2f}ms (p95: {global_results['without_cache']['p95']:.2f}ms)")
    print(f"   Con caché:  {global_results['with_cache']['avg']:.2f}ms (p95: {global_results['with_cache']['p95']:.2f}ms)")
    print(f"   Mejora:     {global_results['improvement_factor']:.2f}x más rápido")
    print(f"   Hit rate:   {global_results['hit_rate']['hit_rate']:.1f}% ({global_results['hit_rate']['hits']}/{global_results['hit_rate']['total']} hits)")

    # Source Stats
    if source_results:
        print("\n📍 GET /stats/sources/{id} (Source Statistics):")
        print(f"   Sin caché:  {source_results['without_cache']['avg']:.2f}ms (p95: {source_results['without_cache']['p95']:.2f}ms)")
        print(f"   Con caché:  {source_results['with_cache']['avg']:.2f}ms (p95: {source_results['with_cache']['p95']:.2f}ms)")
        print(f"   Mejora:     {source_results['improvement_factor']:.2f}x más rápido")
        print(f"   Hit rate:   {source_results['hit_rate']['hit_rate']:.1f}% ({source_results['hit_rate']['hits']}/{source_results['hit_rate']['total']} hits)")

    print("\n" + "=" * 60)
    print("✅ Benchmarks completados")
    print("=" * 60)


# ==================== MAIN ====================


def main():
    """Ejecuta todos los benchmarks."""
    print("🚀 CACHE PERFORMANCE BENCHMARKING")
    print(f"   API: {API_BASE_URL}")
    print(f"   Warmup requests: {WARMUP_REQUESTS}")
    print(f"   Benchmark requests: {BENCHMARK_REQUESTS}")
    print(f"   Mixed load requests: {MIXED_LOAD_REQUESTS}")

    # Verificar que el servidor está corriendo
    try:
        response = requests.get(f"{API_BASE_URL.replace('/api/v1', '')}/health", timeout=5)
        if response.status_code != 200:
            print("❌ Error: Servidor no está saludable")
            return
    except requests.exceptions.RequestException:
        print("❌ Error: No se puede conectar al servidor en http://localhost:8000")
        print("   Por favor, inicia el servidor con: poetry run uvicorn src.api.main:app")
        return

    # Obtener IDs de fuentes dinámicamente
    try:
        response = requests.get(f"{API_BASE_URL}/stats", timeout=5)
        if response.status_code == 200:
            data = response.json()
            global SOURCE_IDS
            SOURCE_IDS = [source["source_id"] for source in data.get("sources", [])]
            print(f"   Fuentes encontradas: {len(SOURCE_IDS)}")
        else:
            print("⚠️  Advertencia: No se pudieron obtener fuentes, solo se ejecutará benchmark global")
    except Exception as e:
        print(f"⚠️  Error obteniendo fuentes: {e}")

    # Ejecutar benchmarks
    global_results = benchmark_global_stats()

    source_results = None
    if SOURCE_IDS:
        source_results = benchmark_source_stats(SOURCE_IDS[0])

    # Imprimir resumen
    print_summary(global_results, source_results)


if __name__ == "__main__":
    main()
