import unreal
import inspect


def preparing_scene_fake(**kwargs):
    unreal.log(f'Executing {inspect.currentframe().f_code.co_name} with args: {kwargs}')
    unreal.log(f'Got kwargs: {kwargs}')
    total_frames = 100
    text_label = "Preparing the scene..."
    with unreal.ScopedSlowTask(total_frames, text_label) as slow_task:
        slow_task.make_dialog(True)  # Makes the dialog visible, if it isn't already
        for i in range(total_frames):
            if slow_task.should_cancel():  # True if the user has pressed Cancel in the UI
                break

            slow_task.enter_progress_frame(1)
            unreal.log(f'Preparing progress: {i}/{total_frames}')


def main(**kwargs):
    preparing_scene_fake(**kwargs)
