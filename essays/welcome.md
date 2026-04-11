Title: Welcome
Slug: welcome
Date: 2026-04-09
Summary: A short first post for the blog.

## Why this exists

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Integer vulputate
rhoncus ullamcorper. Sed condimentum, risus sit amet suscipit imperdiet, dolor
nisl posuere velit, et interdum mauris neque at velit.[^welcome-note]

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Donec feugiat, metus a
lobortis blandit, tortor neque tempor neque, ut bibendum justo neque vitae
erat. Pellentesque viverra feugiat neque, ut ultrices lacus sollicitudin nec.

## Notes and quotations

> Lorem ipsum dolor sit amet, consectetur adipiscing elit. Praesent semper
> fermentum ipsum, eget fringilla purus sodales vel.

Lorem ipsum dolor sit amet, consectetur adipiscing elit. In varius finibus
semper. Aenean at ligula id libero iaculis interdum. Vestibulum ut nibh a enim
interdum commodo.[^notes-footnote]

## Code and examples

```rust
fn fib(n: u32) -> u64 {
    match n {
        0 => 0,
        1 => 1,
        _ => fib(n - 1) + fib(n - 2),
    }
}

fn main() {
    for n in 0..10 {
        println!("fib({n}) = {}", fib(n));
    }
}
```

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Integer ornare
ullamcorper turpis, vitae pharetra sapien fermentum sit amet.

## Reading flow

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Integer vulputate
rhoncus ullamcorper. Sed condimentum, risus sit amet suscipit imperdiet, dolor
nisl posuere velit, et interdum mauris neque at velit. Integer ac posuere
mauris. Sed vitae orci consequat, suscipit justo vel, scelerisque lorem.

### A small subsection

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Donec feugiat, metus a
lobortis blandit, tortor neque tempor neque, ut bibendum justo neque vitae
erat. Pellentesque viverra feugiat neque, ut ultrices lacus sollicitudin nec.

## Footnotes

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Quisque dapibus
maximus arcu, vitae eleifend neque volutpat vel. Sed tincidunt posuere
consequat.[^preview-note]

[^welcome-note]: Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
[^notes-footnote]: Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
[^preview-note]: Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
