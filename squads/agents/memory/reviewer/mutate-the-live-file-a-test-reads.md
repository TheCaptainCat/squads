---
summary: 'A test reading a live project file breaks when that file moves: mutate the
  file'
created_at: '2026-10-11T22:16:09Z'
---
A test that reads a live project file (this repository's own override, a config, a manifest)
is coupled to everything that file will become, not only to what it holds today. Two
mutations find the coupling in a minute, and both found a defect on REV-998:

1. **Move the thing the file is stamped against.** Set the package version forward in a
   scratch copy. A test asserting the stamp equals the running version goes red at the next
   bump even though the tool itself calls the file current.
2. **Add one unrelated, valid entry to the file.** A comparison over a whole output list goes
   red for an addition that has nothing to do with what it pins. Check the board for the next
   feature that will write to that file; here it was already Ready.

Also check what the guard compares: a containment over bare names passed a demoted level.
Mutate in a scratch copy of the tree (`git archive HEAD | tar -x`, run with `PYTHONPATH` at
the copy's `src`), never in the worktree under review.