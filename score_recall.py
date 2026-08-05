"""Score SR1 vocal recall from Penn TotalRecall annotations.

Usage:
    .venv/bin/python score_recall.py data/UT<subject>

For every list with both a .lst file (presented order, written by the task)
and a .ann file (word onsets, written by annotating the .wav in Penn
TotalRecall), this computes serial-recall measures and writes:

    <subject_dir>/scores.csv   one row per annotated word:
        list, output_pos, word, onset_ms, presented_pos, transposition,
        outcome (correct | transposition | repetition | intrusion),
        eeg_time_sec (RecordingStart sync pulse + onset, when available)

    <subject_dir>/summary.csv  one row per list:
        list, n_presented, n_recalled, n_correct_position, n_transposed,
        mean_abs_transposition, n_omissions, n_intrusions, n_repetitions

It also back-fills the reserved `Retrieval_index` and `Distance` columns of
each scored list's `Encoding` rows in events.csv, so the serial-recall
result for every presented word lives alongside the timing log:
    Retrieval_index = output position it was recalled at ("omitted" if never)
    Distance        = transposition (output position - presented position)

Transposition = output position - presented position (0 = recalled in the
correct serial position). Non-word annotations (<IV>, VV, etc.) are ignored.
"""

import csv
import os
import sys
import glob
import re

NON_WORD_CODES = {'<IV>', 'IV', 'VV', '<VV>', '!', '?'}


def read_lst(path):
    with open(path) as f:
        return [w.strip().upper() for w in f if w.strip()]


def read_ann(path):
    """Return [(onset_ms, word), ...] in row order. Rows: onset<TAB>idx<TAB>word."""
    out = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = re.split(r'[\t,]+|\s{2,}', line)
            if len(parts) < 2:
                parts = line.split()
            try:
                onset = float(parts[0])
            except ValueError:
                continue
            word = parts[-1].strip().upper()
            if word and word not in NON_WORD_CODES:
                out.append((onset, word))
    return out


def read_recording_starts(subject_dir):
    """list number -> RecordingStart sync-pulse time (sec), from events.csv."""
    starts = {}
    events_path = os.path.join(subject_dir, 'events.csv')
    if not os.path.isfile(events_path):
        return starts
    with open(events_path) as f:
        for row in csv.DictReader(f):
            if row.get('Event_type') == 'RecordingStart':
                try:
                    starts[int(row['List'])] = float(row['Retrieval_Time'])
                except (ValueError, KeyError):
                    pass
    return starts


def update_events_csv(subject_dir, word_result, scored_lists):
    """Back-fill Retrieval_index and Distance in events.csv Encoding rows.

    word_result: {(list_num, WORD): (output_pos, transposition)} for each
    recalled list word. scored_lists: list numbers that had a .ann (only
    these lists are touched; un-annotated lists keep their blank columns).
    A presented word absent from word_result was omitted at recall.
    """
    path = os.path.join(subject_dir, 'events.csv')
    if not os.path.isfile(path):
        print("events.csv not found -- skipped back-fill")
        return
    with open(path, newline='') as f:
        rows = list(csv.reader(f))
    if not rows:
        return
    header = rows[0]
    try:
        i_type = header.index('Event_type')
        i_list = header.index('List')
        i_word = header.index('Word')
        i_ret = header.index('Retrieval_index')
        i_dist = header.index('Distance')
    except ValueError:
        print("events.csv missing expected columns -- skipped back-fill")
        return

    filled = 0
    for row in rows[1:]:
        if len(row) <= i_dist or row[i_type] != 'Encoding':
            continue
        try:
            lst = int(row[i_list])
        except ValueError:
            continue
        if lst not in scored_lists:
            continue
        key = (lst, row[i_word].strip().upper())
        if key in word_result:
            output_pos, transposition = word_result[key]
            row[i_ret] = output_pos
            row[i_dist] = transposition
        else:
            row[i_ret] = 'omitted'
            row[i_dist] = ''
        filled += 1

    with open(path, 'w', newline='') as f:
        csv.writer(f).writerows(rows)
    print(f"Back-filled Retrieval_index/Distance on {filled} Encoding rows in events.csv")


def score_subject(subject_dir):
    rec_starts = read_recording_starts(subject_dir)
    detail_rows, summary_rows = [], []
    word_result = {}      # (list_num, WORD) -> (output_pos, transposition)
    scored_lists = set()  # list numbers that had a .ann

    lst_files = sorted(glob.glob(os.path.join(subject_dir, '*_list*.lst')),
                       key=lambda p: int(re.search(r'list(\d+)\.lst$', p).group(1)))
    if not lst_files:
        sys.exit(f"No .lst files found in {subject_dir}")

    for lst_path in lst_files:
        list_num = int(re.search(r'list(\d+)\.lst$', lst_path).group(1))
        ann_path = lst_path[:-4] + '.ann'
        presented = read_lst(lst_path)
        if not os.path.isfile(ann_path):
            print(f"list {list_num}: no .ann yet (annotate "
                  f"{os.path.basename(lst_path[:-4])}.wav in Penn TotalRecall) -- skipped")
            continue

        scored_lists.add(list_num)
        annotations = read_ann(ann_path)
        seen = set()
        n_correct = n_transposed = n_intrusions = n_repetitions = 0
        abs_transpositions = []

        output_pos = 0
        for onset, word in annotations:
            eeg_time = (f"{rec_starts[list_num] + onset / 1000.0:.3f}"
                        if list_num in rec_starts else '')
            if word in seen:
                outcome, presented_pos, transposition = 'repetition', '', ''
                n_repetitions += 1
            elif word in presented:
                seen.add(word)
                output_pos += 1
                presented_pos = presented.index(word) + 1
                transposition = output_pos - presented_pos
                abs_transpositions.append(abs(transposition))
                word_result[(list_num, word)] = (output_pos, transposition)
                if transposition == 0:
                    outcome = 'correct'
                    n_correct += 1
                else:
                    outcome = 'transposition'
                    n_transposed += 1
            else:
                outcome, presented_pos, transposition = 'intrusion', '', ''
                n_intrusions += 1
            detail_rows.append([list_num, output_pos if outcome in ('correct', 'transposition') else '',
                                word, f"{onset:.1f}", presented_pos, transposition,
                                outcome, eeg_time])

        n_recalled = n_correct + n_transposed
        mean_abs = (f"{sum(abs_transpositions) / len(abs_transpositions):.2f}"
                    if abs_transpositions else '')
        summary_rows.append([list_num, len(presented), n_recalled, n_correct,
                             n_transposed, mean_abs,
                             len(presented) - n_recalled, n_intrusions, n_repetitions])
        print(f"list {list_num}: {n_recalled}/{len(presented)} recalled, "
              f"{n_correct} in correct position, {n_transposed} transposed"
              f"{' (mean |distance| ' + mean_abs + ')' if mean_abs else ''}, "
              f"{len(presented) - n_recalled} omitted, {n_intrusions} intrusions")

    if not summary_rows:
        sys.exit("Nothing scored -- no .ann files found.")

    with open(os.path.join(subject_dir, 'scores.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['list', 'output_pos', 'word', 'onset_ms', 'presented_pos',
                    'transposition', 'outcome', 'eeg_time_sec'])
        w.writerows(detail_rows)
    with open(os.path.join(subject_dir, 'summary.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['list', 'n_presented', 'n_recalled', 'n_correct_position',
                    'n_transposed', 'mean_abs_transposition', 'n_omissions',
                    'n_intrusions', 'n_repetitions'])
        w.writerows(summary_rows)
    print(f"\nWrote {os.path.join(subject_dir, 'scores.csv')}")
    print(f"Wrote {os.path.join(subject_dir, 'summary.csv')}")
    update_events_csv(subject_dir, word_result, scored_lists)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit("Usage: python score_recall.py data/UT<subject>")
    score_subject(sys.argv[1])
