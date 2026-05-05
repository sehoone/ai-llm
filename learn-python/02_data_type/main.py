def main():
    print("Hello from 02-data-type!")

    # data type
    print(type(1000))
    print(type("1000"))

    print(10*3)
    print("hi my name is 'sehoon'")
    print("hi" * 3)

    name = "sehoon"
    print(id(name))
    print("-------------------------------------------------------")

    # string formatting. f-string
    kr_symbol = "₩"
    kr_price = 1000
    print(f"가격은 {kr_price}{kr_symbol}입니다.")
    print("가격은 {}{}입니다.".format(kr_price, kr_symbol))

    # 2.6 타입 변환
    str_year = "2026"
    # str_year + 1 # error

    int_year = int(str_year)
    print(int_year + 1)

    print("-------------------------------------------------------")
    # 3.1 리스트
    # 리스트는 여러 개의 값을 하나의 변수에 저장할 수 있는 자료형. java의 arraylist와 유사
    icecream = ["chocolate", "vanilla", "strawberry"]
    print(icecream[0])
    print(icecream[0:2]) # slicing

    icecream.append("mint") # add element
    icecream.insert(1, "green tea") # add element at index 1
    print(icecream)

    icecream.remove("green tea") # remove element by value
    del icecream[0] # remove element by index
    print(icecream)

    num1 = [1, 2, 3]
    num2 = [4, 5, 6]
    print(num1 + num2) # list concatenation

    print(f"max: {max(num1)}") # max value in list
    print(f"min: {min(num1)}") # min value in list

    price = [1000, 3000, 2000]
    print(f"sorted price: {sorted(price)}") # sorted list
    print(f"reversed price: {sorted(price, reverse=True)}") # sorted list

    print(price.index(3000)) # index of element

    # 3.2 튜플
    # 튜플은 리스트와 달리 요소를 변경할 수 없는 자료형. java의 final array와 유사
    price2 = (1000, 3000, 2000)
    print(price2[0])
    # price2[0] = 5000 # error

    # 3.3 딕셔너리
    # 딕셔너리는 키-값 쌍으로 데이터를 저장하는 자료형. java의 hashmap과 유사
    person = {
        "name": "sehoon",
        "age": 30,
        "city": "seoul"
    }
    print(person.get("name")) # get value by key

    person["name"] = "sehoon2" # update value by key
    print(person.get("name"))

    del person["age"] # remove key-value pair
    print(person)

if __name__ == "__main__":
    main()
