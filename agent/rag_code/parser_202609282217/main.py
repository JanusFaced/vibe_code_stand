import numpy as np
import os

def main():

    a_vector = np.array([1, 2, 3, 4, 5])
    b_vector = np.array([6, 7, 8, 9, 10])

    c_vector = a_vector + b_vector
    print(c_vector)

    c_vector = a_vector - b_vector
    print(c_vector)

    c_vector = a_vector * b_vector
    print(c_vector)

    c_vector = a_vector / b_vector
    print(c_vector)

if __name__ == "__main__":
    main()