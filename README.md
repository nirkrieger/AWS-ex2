# AWS-ex2
## Introduction
### In general?
>In this exercise, you’ll need to build a queue & work management system for parallel processing.
Assume that you need to run a computation over data submitted by users. For the purpose of this exercise, we’ll assume that they upload a small binary data (16 – 256 KB) and we need to compute some number of SHA512 iterations on the data.
### endpoints
>You’ll need to create a system, which will offer the following endpoints:
```PUT /enqueue?iterations=num```
 with the body containing the actual data.
The response for this endpoint would be the id of the submitted work (to be used later)
```POST /pullCompleted?top=num```
return the latest completed work items (the final value for the work and the work id). ```

## Solution
2 ec2 instances:

1. enqueue instance - Flask server with route of enqueue, method PUT
2. pullCompleted 