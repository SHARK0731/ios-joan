# 한국 LG V30 (LGM-V300S/K/L) iOS 16 (XNU) 포팅 & 부팅 완벽 가이드

이 문서는 **한국판 LG V30 (LGM-V300S / LGM-V300K / LGM-V300L / LGM-V300K0/L0 등, 코드명: `joan`)** 사용자가 본 리포지토리를 활용하여 Apple iOS 16 (XNU 커널)을 직접 빌드하고 부팅하기 위한 상세 단계별 가이드입니다.

---

## 1. 사전 필수 요구 사항

1. **기기**: 한국 LG V30 (SKT / KT / LGU+ / 자급제 모델)
   - SoC: Qualcomm Snapdragon 835 (MSM8998)
   - RAM: 4GB LPDDR4x
   - 스토리지: 64GB / 128GB UFS 2.1
2. **PC 환경**:
   - Ubuntu / Debian Linux 환경 (또는 WSL2 / macOS)
   - 필요 패키지: `fastboot`, `adb`, `mkbootimg`, `aarch64-linux-gnu-gcc`, `apfs-fuse`, `hfsprogs`, `android-sdk-libsparse-utils`
3. **USB 케이블**: 신뢰할 수 있는 USB-A to Type-C 정품 또는 고품질 데이터 케이블

---

## 2. 1단계: LG V30 부트로더 언락 & 필수 파티션 백업

LG전자의 공식 언락 키 발급 서비스가 2021년 12월 31일부로 종료되었습니다.
따라서 한국 출시 모델(V300S/K/L)은 XDA 개발자 커뮤니티에서 검증된 **WTF (Whatever To Fastboot / Frank_Script)** 취약점 공격 방식을 통해 언락해야 합니다.

### (1) EDL (Emergency Download, 9008) 모드를 통한 백업
> [!CAUTION]
> 기기 고유의 모뎀 및 센서 캘리브레이션 데이터는 한 번 손상되면 복구가 불가능합니다. 플래시 전 반드시 백업하십시오!

- QPST 및 QFIL 툴을 실행합니다.
- 기기 전원을 끄고 볼륨 상(+) 또는 볼륨 하(-)를 누른 상태에서 케이블을 연결하거나 9008 진입 키 조합을 사용하여 `Qualcomm HS-USB QDLoader 9008` 포트를 인식시킵니다.
- QFIL의 Partition Manager를 열고 다음 파티션을 PC로 Read Data(덤프)합니다:
  - `persist`, `modemst1`, `modemst2`, `fsg`, `fsc`
  - `boot`, `recovery`, `laf`, `abl`

### (2) WTF 익스플로잇 적용 & fastboot 진입
- V30 초기 엔지니어링 `abl` 이미지를 주입하여 부트로더의 fastboot 메뉴를 활성화합니다.
- 전원을 끄고 `볼륨 하(-) + 전원` 버튼을 누르고 있으면 화면에 fastboot 모드가 표시됩니다.
- PC의 터미널에서 다음 명령을 실행하여 부트로더를 언락합니다:
  ```sh
  fastboot oem unlock
  fastboot reboot bootloader
  ```

### (3) 순정 DTB 추출
- 순정 `boot.img` 파일에서 디바이스 트리 블롭(DTB)을 추출합니다:
  ```sh
  python3 tools/unpack_bootv2.py backup/boot.img dtb/boot_unpacked
  # -> dtb/boot_unpacked/dtb 확인
  ```

---

## 3. 2단계: XNU 커널 빌드

이 프로젝트의 XNU 커널은 Apple의 공식 오픈소스 XNU(xnu-8796)에 Snapdragon 835 (MSM8998) 및 LG V30용 드라이버/패치가 적용되어 있습니다.

GitHub Actions를 통해 무료 macOS 14 러너에서 빌드할 수 있습니다:

1. 본 GitHub 리포지토리를 포크(Fork)합니다.
2. `Actions` 탭으로 이동하여 `xnu` 워크플로를 선택하고 `Run workflow`를 클릭합니다.
3. 빌드가 완료되면 `xnu-kernel` 아티팩트(`kernel.development.sweet`)를 다운로드하여 리포지토리의 `xnu/out/` 경로에 배치합니다:
   ```sh
   mkdir -p xnu/out
   cp ~/Downloads/kernel.development.sweet xnu/out/kernel.development.sweet
   ```

---

## 4. 3단계: 순정 iPhone X iOS 16.7.16 루트 이미지 제작

Apple 공식 서버에서 **iPhone X (iPhone10,3)**용 iOS 16.7.16 (20H392) IPSW를 준비합니다:

```sh
# 1. IPSW 내 디스크 이미지(OS.dmg, SystemOS.dmg, AppOS.dmg) 준비
# 2. 16GB 크기의 HFS+ 저널링 볼륨 생성 및 병합
tools/mkiosroot.sh OS.dmg SystemOS.dmg AppOS.dmg ios16-root.img 16G
sudo fsck.hfsplus -fy ios16-root.img

# 3. LG V30 환경을 위한 유저랜드 최적화 트윅 적용
sudo mount -t hfsplus -o loop,force ios16-root.img /mnt/iosroot
sudo python3 tools/sweet-root-tweaks.py /mnt/iosroot
sudo umount /mnt/iosroot

# 4. 안드로이드 sparse image 포맷으로 변환
img2simg ios16-root.img ios16-root.simg
```

---

## 5. 4단계: LG V30용 ADT 빌드 및 shim-boot.img 생성

MSM8998 하드웨어 주소(GICv3, 1440x2880 프레임버퍼, UFS 2.1, 4GB RAM 맵)를 적용한 Apple Device Tree와 부트 이미지를 생성합니다:

```sh
# 1. ADT 생성
python3 tools/mkadt.py shim/out/joan.adt --highmem

# 2. 커널 + ADT + 부트 아규먼트 패킹
python3 tools/mkpayload.py xnu/out/kernel.development.sweet shim/out/joan.adt shim/out/payload.bin \
    --cmdline 'debug=0xc serial=3 cpus=4 keepsyms=1 -enable_kprintf_spam -noprogress rd=ufsroot0 unentitled_ios_sim_launch=1 ignition_level=1 wdt_test=no_user_checkin ufsrw=1 rootrw=1 launchd_unsecure_cache=1 wdt=-1 sweetfb_noconsole=1 sweetfb_hz=30 sweettouch=0 sweetkeys=0'

# 3. LG V30 부트 헤더 사양으로 shim 부트 이미지 빌드
shim/build.sh ../shim/out/payload.bin
# -> shim/out/shim-boot.img 완성!
```

---

## 6. 5단계: userdata 플래시 및 부팅 테스트

1. V30을 fastboot 모드로 연결합니다.
2. `userdata` 파티션에 준비된 iOS 16 루트 이미지를 기록합니다:
   ```sh
   fastboot -S 512M flash userdata ios16-root.simg
   ```
3. 부트 파티션을 영구 변조하지 않고, `fastboot boot`를 통해 메모리로 직접 일시 부팅합니다:
   ```sh
   fastboot boot shim/out/shim-boot.img
   ```
4. 화면 상태 확인:
   - 부트 심(shim) 콘솔이 `0x9d400000` 프레임버퍼에 흰색 디버그 밴드와 함께 초기화 메시지를 출력합니다.
   - XNU 커널로 핸드오프된 후 Apple 로고가 중앙에 표시됩니다.
   - 약 3~4분 후 iOS 16 SpringBoard 화면이 표시됩니다!

---

## 7. 6단계: 트러블슈팅 및 로그 덤프

부팅 중 문제가 발생하거나 크래시가 일어난 경우:
1. 전원 + 볼륨 하(-)를 길게 눌러 fastboot 모드로 복귀합니다.
2. V30용 TWRP 리커버리로 일시 부팅합니다:
   ```sh
   fastboot boot recovery/twrp-joan.img
   ```
3. 리커버리 ADB가 연결되면 커널 로그 덤프 스크립트를 실행합니다:
   ```sh
   tools/sweet-log-pull.sh logs/v30_kernel.txt
   ```
4. `logs/v30_kernel.txt`에서 `CRASH`, `PANIC`, `SWEET`, `GIC`, `UFS` 키워드를 검색하여 진단합니다.
