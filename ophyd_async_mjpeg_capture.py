import asyncio
from dodal.beamlines import i04

# instantiate smargon device and get omega angle
smargon = i04.smargon()
smargon.wait_for_connection()

# instantiate oav and get zoom value and pixel per micron
oav = i04.oav()
oav.wait_for_connection()

smargon_omega_angle = (smargon.omega.get().user_readback,)
zoom_percentage = (oav.zoom_controller.percentage.get(),)
microns_per_x_pixel = (oav.parameters.micronsPerXPixel,)
microns_per_y_pixel = (oav.parameters.micronsPerYPixel,)
beam_centre_i = (oav.parameters.beam_centre_i,)
beam_centre_j = (oav.parameters.beam_centre_j,)

print(
    smargon_omega_angle,
    zoom_percentage,
    microns_per_x_pixel,
    microns_per_y_pixel,
    beam_centre_i,
    beam_centre_j,
)
