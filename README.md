[![PyPi Version](http://img.shields.io/pypi/v/DirTreeDigest.svg)](https://pypi.python.org/pypi/DirTreeDigest)
[![Travis Build Status](https://travis-ci.org/MartyMacGyver/DirTreeDigest.svg?branch=master)](https://travis-ci.org/MartyMacGyver/DirTreeDigest)
[![License](https://img.shields.io/badge/license-Apache2.0-yellow.svg)](https://www.apache.org/licenses/LICENSE-2.0)

# DirtreeDigest

A tool for generating cryptographic digests and collecting stats across a directory tree

## WORK IN PROGRESS - UNDER DEVELOPMENT AND TEST

Released under the Apache 2.0 license

## Overview

This project was born of necessity many years ago to ensure the integrity of arbitrary disk data, from the data itself right down to its attributes. To do so, the first version of this tool `TreeHash` was created in Perl 5 (which is presented within for posterity and reference only). It's quite a bit of code and while it served its purpose well, it isn't Unicode-savvy and ... well, it's Perl, which I've moved away from since then. Far away. No forwarding address far away.

This second iteration - in Python 3 and leveraging `multiprocessing` - performs multiple simultaneous hashes using multiple worker processes so as to hash each block of data more efficiently. As Windows is one platform I use this on a lot, `spawn` semantics and tradeoffs limit any possible benefits `fork` might provide (however, some would argue that's not such a bad thing either).

Hash digest functions can vary significantly in terms of maximum speed, and the most common ones are almost exclusively streaming. Therefore, the speed gains this aims to achieve aren't from improving the already highly-optimized hashing functions themselves, but from optimizing the way they are carried out.

Given that, there are a few ways to deal with multiple digesting/hashing:

1. Simply hash the data consecutively:

    Lots of external I/O == slow.

2. Give each concurrent worker process a filename and let each one open and hash it:

    Lots of external, potentially conflicting/overlapping I/O. Not so bad on SSD, but with spinning media you'll start getting a lot of seek operations back and forth. While system buffering may hide some of that, eventually the read times will plummet on large files. With tape? Forget it.

3. Give each worker process a pre-read chunk of data via a queue to hash:

    This is where it gets interesting: you're no longer reading the data multiple times, just once, and you're only limited by the showest hash.
    
    However, the fact that all the data needs to be queued multiple times (copying it once for each worker process) leads to significant overhead at scale - even just running `no-op` digests (performing no actual calculations) show a steady decline in performance as the number of processes increases, while internal I/O (obvious on Windows, unclear on others) jumps.
    
    That said, for slower media (e.g., spinning disks) this is still significantly better than sequential hashing.

4. Give each worker process a pre-read chunk of data via a read-only memory mapped buffer to hash:

    In theory the ideal solution would be read-only shared memory, that would be written to one and which each worker could read from independently. The first try used shared buffers with `multiprocessing.sharedctypes` (which cannot be pickled and so cannot be sent to a spawned process) and `multiprocessing.Array` (which worked but was quite slow and was still effectively a copy process). The GIL seemed set against this idea.
    
    Then `mmap` was tried. In Windows if you created a shared memory buffer using `mmap.mmap(0, BIGCHUNKSIZE, 'SomeName1')` you can get to it from the worker processes via the same tag `SomeName1`. This doesn't require disk backing (which would defeat the purpose of reducing media I/O) and indeed, the performance was noticeably better than queueing. (It's not clear how to tackle this in Linux yet.)

Moderate performance improvements for large files come from the use of a small ring of buffers for pre-caching, so as to have sufficient data ready for hashing when the workers are done with previous units.

There was also the question of creating on-demand workers or long-running workers. This started with the former, but the overhead of spawning workers is neither trivial nor necessary. The model was changed and now the tool spawns each worker as a long-running process while it's in operation.

It turns out that Python's `logging` facility doesn't readily handle Unicode, even in Python 3. This was unexpected and some time was spent learning how to do that correctly.

A debug queue was employed, rather than trying to log from the workers (e.g., for debug purposes) and then post-processing to combine and interleave said logs.

Signal handling is tricky. Signal handling when `multiprocessing` is involved is very tricky. Add `logging` and it's ridiculous. At first custom signal handlers were tried, but they were surprisingly problematic so exception handling to deal with the occasional Ctrl-C (the likeliest commanded abnormal exit).

At a higher level, the architecture is straightforward:

  - Initialize workers (they live as long as the top-level process).
  
  - Walk the directory tree

  - For a given file (the debug queue is read and logged periodically during this):

    - Send "init" command to each worker, telling them to reset and which digest tipe to prepare for

    - Read the first block of the file into shared memory

    - Over the queue, inform all workers that the named shared memory block is ready for digesting

    - While waiting for results, pre-fetch data into the next free buffer(s)

    - Once all workers have finished processing the data block, send them the next available block to process. Repeat.

    - When EOF is reached and cache buffers are exhausted, request final hash data from workers

  - When all files are processed, cleanly shut down the workers and exit

## TODO

  - Cleanups

  - More testing

  - Linux/OS X mmap - the memory tagging trick that works optimally in Windows is different in Linux, and it's not clear how to do this in OS X yet, so less-efficient queueing is used by default  for these (--nomap is always active)
