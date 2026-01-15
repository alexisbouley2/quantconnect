I am on working on quant connect to actually develop a strategy to do so, I am first creating a framework to like execute a strategy etc...

Here the prompt I gave to claude:

```
Ok it is start to begin the implementation of my research ptoject,

so I furst want to create a set of class / functions which I can easily call to test different strategies, quickly optimize on parameters etc....

So when i want to create model and make some research I was thinking about a class where I first
1.  Init the model

With the following params:
set_cash(default to 1000)
set_start_date()
set_end_date()
It will also expect a list of equities  to work with
and the resolution of the data

Then I want the onData function Each time new data happen it execute the strategy, like it tell you what are the new holdings, see what i mean.
Basically when i want to test different strategies variant, I should just provide a different onData function.
I guess this is the onData function that take the params too

Then i want a method that allow to get the stats with a param to know if we want to add the plot or just return the stats as a number
If I have the perfect combination of that, I would both write a script on top of that to iterate over the class, call it with the different variants functions and params setting, call the stats function to get the stats

Then plot the performance evolution depending how you vary one of the stats.

For the stats keep it simple for now we will discuss which stats add afterward
```

Because some functions are proper to the cloud quant connect env, do not worry about some stuff being undefined.
