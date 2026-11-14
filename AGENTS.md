# Working on ios-joan (LG V30)

- Read `NOTES.md` before starting; it contains the project goal, MSM8998 hardware facts,
  current blocker, local artifact locations and the next concrete action.
- Target device: LG V30 / V30+ (LGM-V300S/K/L, codename `joan`, Qualcomm MSM8998 / Snapdragon 835).
- Commit completed changes. Use `gh` for GitHub Actions kernel builds and logs.
- Device bring-up uses temporary `fastboot boot` images (bootloader unlocked via WTF exploit).
  Preserve calibration partitions (`persist`, `modemst1`, `modemst2`, `fsg`, `fsc`) and stock backups.
  The iOS root goes into the existing `userdata` partition.
- Keep device dumps, serial numbers and downloaded Apple artifacts out of git.
