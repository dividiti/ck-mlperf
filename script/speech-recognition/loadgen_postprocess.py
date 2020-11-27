#
# Copyright (c) 2020 cTuning foundation.
# See CK COPYRIGHT.txt for copyright details.
#
# SPDX-License-Identifier: BSD-3-Clause.
# See CK LICENSE.txt for licensing details.
#

import os
import json
import re

MLPERF_LOG_ACCURACY_JSON = 'mlperf_log_accuracy.json'
MLPERF_LOG_DETAIL_TXT    = 'mlperf_log_detail.txt'
MLPERF_LOG_SUMMARY_TXT   = 'mlperf_log_summary.txt'
MLPERF_LOG_TRACE_JSON    = 'mlperf_log_trace.json'

RNNT_TIMING_INSTRUMENTATION_JSON = 'instr_timing.json'
RNNT_ACC_INSTRUMENTATION_JSON    = 'instr_accuracy.json'

LABELS = [" ", "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z", "'"]

def logits_to_string(logits, labels):
    labels_map = dict([(i, labels[i]) for i in range(len(labels))])
    return ''.join([labels_map[c] for c in logits])

def keyval(d, key):
  for k,v in d.items():
    if isinstance(v, dict):
        result = keyval(v, key)
        if result != None:
          return result
    else:
        if(k == key):
          return v

def ck_postprocess(i):
  print('\n--------------------------------')

  save_dict = {}

  # Save logs.
  save_dict['mlperf_log'] = {}
  mlperf_log_dict = save_dict['mlperf_log']

  with open(MLPERF_LOG_ACCURACY_JSON, 'r') as accuracy_file:
    mlperf_log_dict['accuracy'] = json.load(accuracy_file)

  with open(MLPERF_LOG_SUMMARY_TXT, 'r') as summary_file:
    unstripped_summary_lines = summary_file.readlines()
    mlperf_log_dict['summary'] = unstripped_summary_lines

    save_dict['parsed_summary'] = {}
    parsed_summary = save_dict['parsed_summary']
    for line in unstripped_summary_lines:
      pair = line.strip().split(': ', 1)
      if len(pair)==2:
        parsed_summary[ pair[0].strip() ] = pair[1].strip()

  with open(MLPERF_LOG_DETAIL_TXT, 'r') as detail_file:
    mlperf_log_dict['detail'] = detail_file.readlines()

  import os
  if os.stat(MLPERF_LOG_TRACE_JSON).st_size==0:
    mlperf_log_dict['trace'] = {}
  else:
    with open(MLPERF_LOG_TRACE_JSON, 'r') as trace_file:
      mlperf_log_dict['trace'] = json.load(trace_file)

  # Check accuracy in accuracy mode.
  accuracy_mode = False
  if mlperf_log_dict['accuracy'] != []:
    accuracy_mode = True

  if os.path.isfile(RNNT_TIMING_INSTRUMENTATION_JSON) and \
     os.path.isfile(RNNT_ACC_INSTRUMENTATION_JSON):
    instrumentation = []

    # Open the json manifest
    man_path = keyval(i, 'CK_ENV_DATASET_AUDIO_PREPROCESSED_DIR')
    man_path = os.path.join(man_path, 'wav-list.json')
    with open(man_path, 'r') as manifest_file:
      manifest = json.load(manifest_file)

    with open(RNNT_TIMING_INSTRUMENTATION_JSON, 'r') as instr_file:
      timings = json.load(instr_file)

    with open(RNNT_ACC_INSTRUMENTATION_JSON, 'r') as instr_file:
      accuracy = json.load(instr_file)

    for s in accuracy['samples']:
      sample = {}
      sample['hypothesis']=logits_to_string(s['hypothesis'], LABELS)
      sample['reference']=logits_to_string(s['reference'], LABELS)

      #from metrics import word_error_rate
      #wer, scores, num_words = word_error_rate(
      #    [sample['hypothesis']], references=[sample['reference']])
      wer, scores, num_words = 0,0,0

      for t in timings['samples']:
          if s['result']['qsl_idx'] == t['qsl_idx']:
              sample['total_time'] = t['total_time']
              sample['pre_time'] = t['pre_time']
              sample['post_time'] = t['post_time']
              sample['dec_time'] = t['dec_time']

      for m in manifest:
          if sample['reference'] == m['transcript']:
              sample['duration']=m['original_duration']
              sample['audio_filepath']=m['files'][0]['fname']

      sample['wer'] = wer
      sample['scores'] = scores
      sample['num_words'] = num_words
      sample['qsl_idx'] = s['result']['qsl_idx']

      instrumentation.append(sample)

    save_dict['instrumentation'] = { 'wer': accuracy['wer'], \
                                     'samples': instrumentation}

    save_dict['execution_time'] = timings['execution_time']

  with open('tmp-ck-timer.json', 'w') as save_file:
    json.dump(save_dict, save_file, indent=2, sort_keys=True)

  print('--------------------------------\n')
  return {'return': 0}

