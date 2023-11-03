#include "foo.h"

int foo_init(foo_t *foo){
    foo->counter = 0;
    return FOO_OK;
}

int foo_increment(foo_t *foo){
    foo->counter++;
    return foo->counter;
}
