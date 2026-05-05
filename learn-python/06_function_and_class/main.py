def main():
    print("Hello from 06-function!")

    # 함수
    # def 함수명(매개변수):
    #     실행할 코드
    #     return 반환값

    def hello(name):
        age = 30
        print(f"Hello, {name}!")
        print(f"Your age is {age}.")
        
    hello("Alice")

    # class
    # class 클래스명:
    #     def __init__(self, 매개변수):
    #         self.속성 = 매개변수
    #     def 메서드(self):

    class Person:
        # 생성자 메서드. 객체가 생성될 때 자동으로 호출되는 메서드.
        def __init__(self, name, age):
            self.name = name
            self.age = age
        
        def introduce(self):
            print(f"Hello, my name is {self.name} and I am {self.age} years old.")

    person = Person("Alice", 30)
    person.introduce()

    person2 = Person("Bob", 25)
    person2.introduce()

    # 클래스 상속
    class Student(Person):
        def __init__(self, name, age, student_id):
            super().__init__(name, age) # 부모 클래스의 생성자 호출
            self.student_id = student_id
        
        def introduce(self):
            super().introduce() # 부모 클래스의 메서드 호출
            print(f"My student ID is {self.student_id}.")

    student = Student("Charlie", 20, "S12345")
    student.introduce()

if __name__ == "__main__":
    main()
