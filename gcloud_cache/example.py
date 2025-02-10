import time
import asyncio
from cache import cache_result  # Zakładamy, że dekorator caching jest dostępny jako "cache"

@cache_result
def complex_sync_function(x, y, delay=2):
    """Funkcja synchroniczna symulująca złożone obliczenia."""
    print(f"Computing sync result for {x} and {y} (delay={delay})")
    time.sleep(delay)
    # Przykładowy złożony wzór
    return (x * y) + (x ** 2) - (y ** 2)

@cache_result
async def complex_async_function(x, y, delay=2):
    """Asynchroniczna wersja funkcji symulująca złożone obliczenia."""
    print(f"Computing async result for {x} and {y} (delay={delay})")
    await asyncio.sleep(delay)
    return (x + y) * (x - y)

def main():
    # Test funkcji synchronicznej
    print("Pierwsze wywołanie funkcji sync:")
    result1 = complex_sync_function(3, 4)
    print("Wynik:", result1)
    print("Drugie wywołanie funkcji sync (powinno wykorzystać cache):")
    result2 = complex_sync_function(3, 4)
    print("Wynik:", result2)
    
    # Test funkcji asynchronicznej
    print("\nPierwsze wywołanie funkcji async:")
    result_async1 = asyncio.run(complex_async_function(5, 2))
    print("Wynik:", result_async1)
    print("Drugie wywołanie funkcji async (powinno wykorzystać cache):")
    result_async2 = asyncio.run(complex_async_function(5, 2))
    print("Wynik:", result_async2)

if __name__ == '__main__':
    main()