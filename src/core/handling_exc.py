def risky_operations(argument):
    try:
        return 1 / argument
    except ZeroDivisionError:
        print("You can't divide by zero!")
        raise


if __name__ == "__main__":
    result = risky_operations(1)
    print(result)

    result = risky_operations(0)
    print(result)
