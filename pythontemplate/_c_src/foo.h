#ifndef FOO_H
#define FOO_H

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    FOO_OK = 0,
} foo_res_t;

typedef struct {
    int counter;
} foo_t;

int foo_init(foo_t *foo);

int foo_increment(foo_t *foo);

#ifdef __cplusplus
}
#endif

#endif
