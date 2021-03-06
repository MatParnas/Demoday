# -*- coding: utf-8 -*-
"""MusicVAE_custom_0.1.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1BTIb5kP6nQHZuMf7ZW8QmLGYvX10HSp4

# Custom VAE

## Setting up environment

### Imports
"""

import os, random
import glob

BASE_DIR = "gs://download.magenta.tensorflow.org/models/music_vae/colab2"

print('Installing dependencies...')
#!apt-get update -qq && apt-get install -qq libfluidsynth1 fluid-soundfont-gm build-essential libasound2-dev libjack-dev
#!
pip install -q pyfluidsynth
#!
pip install -qU magenta

# Hack to allow python to pick up the newly-installed fluidsynth lib.
# This is only needed for the hosted Colab environment.
import ctypes.util
orig_ctypes_util_find_library = ctypes.util.find_library
def proxy_find_library(lib):
  if lib == 'fluidsynth':
    return 'libfluidsynth.so.1'
  else:
    return orig_ctypes_util_find_library(lib)
ctypes.util.find_library = proxy_find_library


print('Importing libraries and defining some helper functions...')

import magenta.music as mm
from magenta.models.music_vae import configs
from magenta.models.music_vae.trained_model import TrainedModel
import numpy as np
import os
import tensorflow.compat.v1 as tf
import streamlit

tf.disable_v2_behavior()

# Necessary until pyfluidsynth is updated (>1.2.5).
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

"""### Environment"""

def play(note_sequence):
  mm.play_sequence(note_sequence, synth=mm.fluidsynth)

def interpolate(model, start_seq, end_seq, num_steps, max_length=32,
                assert_same_length=True, temperature=0.5,
                individual_duration=4.0):
  """Interpolates between a start and end sequence."""
  note_sequences = model.interpolate(
      start_seq, end_seq,num_steps=num_steps, length=max_length,
      temperature=temperature,
      assert_same_length=assert_same_length)

  print('Start Seq Reconstruction')
  play(note_sequences[0])
  print('End Seq Reconstruction')
  play(note_sequences[-1])
  print('Mean Sequence')
  play(note_sequences[num_steps // 2])
  print('Start -> End Interpolation')
  interp_seq = mm.sequences_lib.concatenate_sequences(
      note_sequences, [individual_duration] * len(note_sequences))
  play(interp_seq)
  mm.plot_sequence(interp_seq)
  return interp_seq if num_steps > 3 else note_sequences[num_steps // 2]



print('Done')

"""## Load the pre-trained models.

### Load Melody model
"""

# Load the pre-trained models.
mel_16bar_models = {}
hierdec_mel_16bar_config = configs.CONFIG_MAP['hierdec-mel_16bar']
mel_16bar_models['hierdec_mel_16bar'] = TrainedModel(hierdec_mel_16bar_config, batch_size=4, checkpoint_dir_or_path=BASE_DIR + '/checkpoints/mel_16bar_hierdec.ckpt')

flat_mel_16bar_config = configs.CONFIG_MAP['flat-mel_16bar']
mel_16bar_models['baseline_flat_mel_16bar'] = TrainedModel(flat_mel_16bar_config, batch_size=4, checkpoint_dir_or_path=BASE_DIR + '/checkpoints/mel_16bar_flat.ckpt')

"""### Load Trio Model"""

# Load the pre-trained models.
trio_models = {}
hierdec_trio_16bar_config = configs.CONFIG_MAP['hierdec-trio_16bar']
trio_models['hierdec_trio_16bar'] = TrainedModel(hierdec_trio_16bar_config, batch_size=4, checkpoint_dir_or_path=BASE_DIR + '/checkpoints/trio_16bar_hierdec.ckpt')

flat_trio_16bar_config = configs.CONFIG_MAP['flat-trio_16bar']
trio_models['baseline_flat_trio_16bar'] = TrainedModel(flat_trio_16bar_config, batch_size=4, checkpoint_dir_or_path=BASE_DIR + '/checkpoints/trio_16bar_flat.ckpt')

"""## Generate

### Create input MIDI data
"""

def create_input(): 
  # Create a list of 3 usable MIDI paths

  paths = []
  
  while choice != 'Melancholy' and choice != 'Dance':
    choice = (input('Tape D for Dance or S for Sad :')).lower()
  if choice == 'd':
    theme = 'dance/'
  else :
    theme = 'sad/'
  for path in range(3):
    dance_random = random.choice(os.listdir("midi_samples/" + theme))
    while dance_random[0] == '.':
      dance_random = random.choice(os.listdir("midi_samples/" + theme)) 
    path = ('midi_samples/'+ theme + dance_random)
    paths.append(path)
  
  # Use example MIDI files for interpolation endpoints.
  return [
          tf.io.gfile.GFile(fn, 'rb').read()
          for fn in sorted(tf.io.gfile.glob(paths))], theme

"""### Exctract from MIDI"""

def gen_interpolation(input_midi_data,theme):
  input_seqs = [mm.midi_to_sequence_proto(m) for m in input_midi_data]
  if theme == 'sad/':
    # Extract melodies from MIDI files. This will extract all unique 16-bar melodies using a sliding window with a stride of 1 bar.
    
    extracted_16_mels = []
    for ns in input_seqs:
      extracted_16_mels.extend(
          hierdec_mel_16bar_config.data_converter.from_tensors(
              hierdec_mel_16bar_config.data_converter.to_tensors(ns)[1]))
    for i, ns in enumerate(extracted_16_mels):
      print("Melody", i)
      play(ns)
    return extracted_16_mels

  else :
    # Extract trios from MIDI files. This will extract all unique 16-bar trios using a sliding window with a stride of 1 bar.

    extracted_trios = []
    for ns in input_seqs:
      extracted_trios.extend(
          hierdec_trio_16bar_config.data_converter.from_tensors(
              hierdec_trio_16bar_config.data_converter.to_tensors(ns)[1]))
    for i, ns in enumerate(extracted_trios):
      print("Trio", i)
      play(ns)
      return extracted_trios

"""### Generate final wav"""

def gen_final(extracted_16, theme):
  # Compute the reconstructions and mean
  interp_model = ''
  final_model = mel_16bar_models
  if theme == 'sad/':
    interp_model = "baseline_flat_trio_16bar" #@param ["hierdec_mel_16bar", "baseline_flat_mel_16bar"]
  else:
    interp_model = "hierdec_trio_16bar" #@param ["hierdec_trio_16bar", "baseline_flat_trio_16bar"]
    final_model = trio_models


  start = 0 #@param {type:"integer"}
  end = 1 #@param {type:"integer"}
  start = extracted_16[start]
  end = extracted_16[end]

  temperature = 0.5 #@param {type:"slider", min:0.1, max:1.5, step:0.1}
  
  return interpolate(final_model[interp_model], start, end, num_steps=3, max_length=256, individual_duration=32, temperature=temperature), interp_model



#### Streamlit App 

### App config
st.title("DJ DEEPROLLERZ")

st.markdown("""BLABLALA KWBG RULES
""")

st.markdown("---")


### Content

st.subheader("About the project")
st.markdown("""

balblabla on dechire
""")


st.subheader("Create your music")

col1, col2 = st.columns(2)

melody = ['Melancholy','Dance']
generate = form.form_submit_button("Generate")
with col1:

    with st.form("Select your theme"):
        choice = st.selectbox('ahaha', theme)
        input_midi_data, theme = create_input()

        generate = form.form_submit_button("Generate")



with col2:

    if generate:
        with st.spinner("Generating..."):
            while True:
                extracted_16= gen_interpolation(input_midi_data,theme)
                g_16bar_mean,  interp_model= gen_final(extracted_16,theme)

                st.text("play your song")
                st.audio(virtualfile)




