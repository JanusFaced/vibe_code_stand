# main.py
import random

def generate_numbers(count):
    return [random.randint(1, 100) for _ in range(count)]

def analyze_list(numbers):
    if not numbers:
        return None, None, None, None
    max_val = max(numbers)
    min_val = min(numbers)
    avg_val = sum(numbers) / len(numbers)
    total_sum = sum(numbers)
    return max_val, min_val, avg_val, total_sum

def sum_lists(list1, list2):
    return [x + y for x, y in zip(list1, list2)]

def subtract_lists(list1, list2):
    return [x - y for x, y in zip(list1, list2)]

if __name__ == '__main__':
    numbers1 = generate_numbers(10)
    numbers2 = generate_numbers(10)
    print('Generated Numbers 1:', numbers1)
    print('Generated Numbers 2:', numbers2)
    max_val1, min_val1, avg_val1, total_sum1 = analyze_list(numbers1)
    max_val2, min_val2, avg_val2, total_sum2 = analyze_list(numbers2)
    sum_result = sum_lists(numbers1, numbers2)
    subtract_result = subtract_lists(numbers1, numbers2)
    print(f'Maximum 1: {max_val1}, Minimum 1: {min_val1}, Average 1: {avg_val1}, Sum 1: {total_sum1}')
    print(f'Maximum 2: {max_val2}, Minimum 2: {min_val2}, Average 2: {avg_val2}, Sum 2: {total_sum2}')
    print('Sum of Lists:', sum_result)
    print('Difference of Lists:', subtract_result)