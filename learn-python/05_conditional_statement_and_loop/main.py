def main():
    print("Hello from 04-conditional-statement!")

    # 조건문
    # if 조건문:
    #     실행할 코드
    # elif 조건문:
    #     실행할 코드
    # else:
    #     실행할 코드

    coffee_price = 3000
    coffee_size = "tall"

    if coffee_price >= 3000:
        print("커피 주문1")
    
    if (coffee_price == 3000) and (coffee_size == "tall2"):
        print("커피 주문2")
    elif (coffee_price == 3000) and (coffee_size == "tall"):
        print("커피 주문3")

    print("-------------------------------------------------------")
    # 반복문
    # for 반복문
    # for 변수 in 반복 가능한 객체:
    #     실행할 코드
    for i in range(5):
        print(i)

    print("-------------------------------------------------------")
    for i in range(1, 10, 2): # range(start, end, step)
        if i == 5:
            break
        print(i)
    print("-------------------------------------------------------")
    # while 반복문
    # while 조건문:
    #    실행할 코드

    num = 1
    while num <= 3:
        print(f"num: {num}")
        num += 1    

if __name__ == "__main__":
    main()
