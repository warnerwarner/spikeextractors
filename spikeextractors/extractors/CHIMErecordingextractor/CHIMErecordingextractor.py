from spikeextractors import RecordingExtractor
from spikeextractors.extraction_tools import check_get_traces_args
import numpy as np
from pathlib import Path
import sys


try:
    import h5py
    HAVE_CHIME = True
except ImportError:
    HAVE_CHIME = False

try:
    sys.path.append('/home/camp/warnert')
    import chimpy
    HAVE_CHIMPY = True
    print('Found CHIMPY!')
except ImportError:
    HAVE_CHIMPY = False

class CHIMERecordingExtractor(RecordingExtractor):
    extractor_name = 'CHIMERecording'
    has_default_locations = True
    installed = HAVE_CHIME
    is_writable = True
    mode = 'file'
    installation_mesg = "To use the CHIMERecordingExtractor install h5py: \n\n pip install h5py\n\n"  # error message when not installed

    def __init__(self, file_path, verbose=False, sampling_rate=20000):
        assert HAVE_CHIME, self.installation_mesg
        self._recording_file = file_path
        self._sampling_rate = sampling_rate
        self._fid, self._num_chans, self._num_Frames, self._chan_poses = openCHIMEFile(
            file_path, verbose=verbose, sampling_rate=sampling_rate)
        self._read_function = readHDF5
        self._chan_ids = range(len(self._num_chans))
        RecordingExtractor.__init__(self)
        if '.filt.' in self._recording_file:
            self.is_filtered = True
        else:
            self.is_filtered = False
        self.set_channel_locations(self._chan_poses)
        self._kwargs = {"file_path": str(Path(file_path).absolute()), 'verbose':verbose}

    def __del__(self):
        self._fid.close()
    
    def get_channel_ids(self):
        return list(range(self._num_chans))
    
    def get_num_frames(self):
        return self._num_Frames
    
    def get_sampling_frequency(self):
        return self._sampling_rate
    
    @check_get_traces_args
    def get_traces(self, channel_ids=None, start_frame=None, end_frame=None):
        data = self._read_function(self._fid, start_frame, end_frame, chans=self._chan_ids)
        return data[channel_ids]
    
    def make_chimpy_recording(self):
        self._chimpy_recording = chimpy.recording.Recording(self._recording_file)
    
    def update_channels(self):
        self._chimpy_recording.remove_satured()
        self._chimpy_recording.remoce_broken()
        self._num_chans = len(self._chimpy_recording.channels)
        xs = self._chimpy_recording.xs
        ys = self._chimpy_recording.ys
        self._chan_poses = [(i, j) for i, j in zip(xs, ys)]
        self._chan_ids = self._chimpy_recording.channels


def openCHIMEFile(filename, verbose=False, sampling_rate=20000):
    fid = h5py.File(filename, 'r')
    data=fid['sig']
    numChans = len(data)
    numFrames = len(data[0])
    chan_poses = [(i[2], i[3]) for i in fid['mapping']]

    if verbose:
        print('# CHIME recording:', filename)
        print('# number of channels:',numChans)
        print('# length of recording', numFrames/sampling_rate)

    return (fid, numChans, numFrames, chan_poses)
def readHDF5(fid, t0, t1, chans=None):
    if chans is None:
        return fid['sig'][:, t0:t1]
    else:
        return fid['sig'][chans, t0:t1]