#include <stdio.h>

void change(int x) {
    x = 20;
}


int main() {
    int a = 10;
    change(a);
    printf("Value of a = %d", a);
    return 0;
}
//                         func
// variable    a           x
// Value       10          20
// mem addr    1024        1028

//                         func
// variable    a    <------*x
// Value       20          20
// mem addr    1024        1024

// #include <stdio.h>

// void change(int *x) {
//     *x = 20;
// }

// int main() {
//     int a = 10;
//     change(&a); #1024
//     printf("Value of a = %d", a); #20
//     return 0;
// }

// call by value:
// Only a copy is passed
// Original value remains unchanged


// call by reference:
// Address is passed
// Original value is changed