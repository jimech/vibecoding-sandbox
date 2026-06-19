def fibonacci(n):
    fib_sequence = [0, 1]
    while len(fib_sequence) < n:
        next_value = fib_sequence[-1] + fib_sequence[-2]
        fib_sequence.append(next_value)
    return fib_sequence

if __name__ == "__main__":
    n = 10
    print(f"Fibonacci series for {n} numbers: {fibonacci(n)}")