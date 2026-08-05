# Scoring SR1 vocal recall with Penn TotalRecall

The task records one audio file per list of each participant's spoken serial
recall. Scoring (which words were said, in what order, and exactly when) is
done offline with **Penn TotalRecall**, the UPenn Computational Memory Lab's
audio annotation tool: https://memory.psych.upenn.edu/TotalRecall

## Files the task produces (per participant, in `data/UT<subject>/`)

| File | Contents |
|---|---|
| `UT<subject>_list<N>.wav` | Vocal recall audio for list N (44.1 kHz mono). Recording starts just **before** the beep, so the beep audible at the start of each file marks retrieval onset. |
| `UT<subject>_list<N>.lst` | The words of list N in the order they were presented, one per line. |
| `events.csv` | Full event log. `RecordingStart` rows give the sync-pulse time at audio t=0; `Encoding` rows give each word's presented position and encoding pulse. |
| `pulses.csv` | All sync pulse times (experiment clock). |

## Annotation workflow

1. Download and install Penn TotalRecall from the link above (Java app;
   builds are provided for Mac).
2. In TotalRecall, load the wordpool file `resources/ram_wordpool_en.txt`
   so annotations autocomplete against the task's vocabulary.
3. Open a `.wav` file and step through it, marking the **onset of each spoken
   word** and typing the word (use the standard intrusion/vocalization codes
   `<IV>` / `VV` per your lab's convention for non-list utterances).
4. TotalRecall writes a `.ann` file next to the `.wav`: one row per
   annotation with the onset time (ms from the start of the file) and the word.

## Computing serial recall measures from the annotations

Automated: once `.ann` files sit next to the `.wav`/`.lst` files, run

    .venv/bin/python score_recall.py data/UT<subject>

It writes `scores.csv` (one row per annotated word: output position,
transposition distance, outcome, onset, and EEG-aligned time) and
`summary.csv` (per-list totals: recalled, correct-position, transposed,
mean |transposition|, omissions, intrusions, repetitions).

It also **back-fills `events.csv`**: for every scored list, each `Encoding`
row's previously blank `Retrieval_index` and `Distance` columns are filled
with that word's output position and transposition (a presented word never
recalled is marked `Retrieval_index = omitted`). So the serial-recall result
for each word sits right next to its presentation time in the event log.
Lists that haven't been annotated yet keep their blank columns.

The definitions it implements:

- **Output order** comes from the row order of the `.ann` file.
- **Transposition distance** for each correctly recalled word =
  (its output position in the `.ann`) − (its line number in the `.lst`).
  Distance 0 is a correct-position recall; ±k is a transposition of size k.
- **Omissions** are `.lst` words absent from the `.ann`; **intrusions** are
  annotated words absent from the `.lst`; repeated words are counted once
  and flagged as repetitions thereafter. `<IV>`/`VV` codes are ignored.

## Aligning vocalization times to EEG

Each annotation's onset is relative to the start of its audio file. Audio
t=0 corresponds to the `RecordingStart` sync pulse for that list (the
`Retrieval_Time` column of the `RecordingStart` row in `events.csv`, which
also appears in `pulses.csv`). So:

    EEG time of a vocalization = RecordingStart pulse time + (annotation onset in ms / 1000)

The beep at the start of each recording (logged as `RetrievalBeep`, also
sync-pulsed) provides a second alignment check.

## Reference

The serial-recall paradigm and relative-order scoring follow:

> Klein, K. A., Addis, K. M., & Kahana, M. J. (2005). A comparative analysis
> of serial and free recall. *Memory & Cognition, 33*(5), 833–839.
> https://doi.org/10.3758/BF03193078
