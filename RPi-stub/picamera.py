
#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#


class PiCamera:

    def resolution(w, h):
        raise NotImplemented()

    def capture(self, camera, type, use_video_port=True):
        raise NotImplemented()

    def start_preview(self):
        raise NotImplemented()

    def stop_preview(self):
        raise NotImplemented()
