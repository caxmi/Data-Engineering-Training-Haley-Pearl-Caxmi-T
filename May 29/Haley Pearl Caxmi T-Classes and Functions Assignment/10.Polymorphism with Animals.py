class Animal:
    def speak(self):
        return "Generic animal sound"

class Dog(Animal):
    def speak(self):
        return "Woof!"

class Cat(Animal):
    def speak(self):
        return "Meow!"

class Cow(Animal):
    def speak(self):
        return "Moo!"

animals = [Dog(), Cat(), Cow()]
for animal in animals:
    print(f"{animal.__class__.__name__} says: {animal.speak()}")
