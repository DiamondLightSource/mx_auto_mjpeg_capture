from dodal.beamlines import i04
from dodal.devices.smargon import Smargon

import bluesky.plan_stubs as bps

from unittest.mock import MagicMock, patch
from functools import partial
from ophyd.status import Status

from hyperion.device_setup_plans.setup_oav import get_move_required_so_that_beam_is_at_pixel
from murko_results import RedisClient
from murko_trigger import MurkoTrigger
from PV_trigger import PVTrigger
from  uuid import uuid4

def mock_set(motor, val):
    motor.user_setpoint.sim_put(val)  # type: ignore
    motor.user_readback.sim_put(val)  # type: ignore
    return Status(done=True, success=True)

def patch_motor(motor):
    return patch.object(motor, "set", MagicMock(side_effect=partial(mock_set, motor)))

def wait_for_trigger_then_centre(pv_trigger: PVTrigger, murko_trigger: MurkoTrigger, murko_results: RedisClient, oav, smargon:Smargon):
    print("Waiting for trigger PV to go high")
    while True:
        pv_state = yield from bps.rd(pv_trigger.trigger)
        if pv_state:
            yield from centre(murko_trigger, murko_results, oav, smargon)
            yield from bps.abs_set(pv_trigger.trigger, 0)
        else:
            yield from bps.sleep(0.1)


def centre(murko_trigger: MurkoTrigger, murko_results: RedisClient, oav, smargon:Smargon):
    THAW_VELO = 10
    print("Runnin g pplanb")
    murko_trigger.sample_id = str(uuid4())
    for pos in [0, 90]:
        yield from bps.trigger(murko_results, group=f"murko_{pos}")
        print("Triggered murko")

        yield from bps.mv(smargon.omega, pos)
        yield from bps.trigger(murko_trigger, wait=True)

        yield from bps.wait(group=f"murko_{pos}")
        x = yield from bps.rd(murko_results.x)
        y = yield from bps.rd(murko_results.y)
        microns_per_x_pixel = yield from bps.rd(murko_results.microns_per_x_pixel)
        microns_per_y_pixel = yield from bps.rd(murko_results.microns_per_y_pixel)
        print(f"Got in plan {x, y, microns_per_x_pixel, microns_per_y_pixel}")
        # Get p[ixels to microns from OAV
        position = yield from get_move_required_so_that_beam_is_at_pixel(smargon=smargon, pixel=(x,y), oav_params=oav.parameters)
        print(position)
        # Move Smargon
        yield from bps.mv(
            smargon.x,
            position[0],
            smargon.y,
            position[1],
            smargon.z,
            position[2]
        )


def make_smargon(fake):
    if fake:
        smargon = i04.smargon(fake_with_ophyd_sim=True)
        smargon.omega.user_readback.sim_put(0)
        smargon.omega.user_setpoint._use_limits = False
        patch_motor(smargon.omega)
    else:
        smargon = i04.smargon()
    return smargon

def make_oav(fake):
    if fake:
        oav = i04.oav(fake_with_ophyd_sim=True)
    else:
        oav = i04.oav()
    return oav

if __name__ == "__main__":
    print("at start of script  before pickle import")
    import pickle
    from bluesky.run_engine import RunEngine

    from ophyd_async.core import DeviceCollector
    re = RunEngine()
    with DeviceCollector():
        client = RedisClient(host="ws561.diamond.ac.uk")
        pv_trigger = PVTrigger()
    
    murko_trigger = MurkoTrigger(name="murko-trigger", smargon = make_smargon(False), oav = make_oav(False))

    re(wait_for_trigger_then_centre(pv_trigger, murko_trigger, client, make_oav(False), make_smargon(False)))

    print("End of the script")
