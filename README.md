# ios-joan (LG V30 / MSM8998)

**한국 LG V30 스마트폰을 위한 Apple iOS 16 (XNU 커널) 부팅 프로젝트**

이 프로젝트는 Apple의 오픈소스 XNU 커널(xnu-8796, iOS 16 세대)을 **한국 LG V30 (코드명 `joan`, Qualcomm Snapdragon 835 / MSM8998)** 기기에 맞춰 포팅한 리포지토리입니다. 커널 상단에는 **iPhone X의 순정 iOS 16.7.16 (20H392) 유저랜드**(launchd, 시스템 데몬, backboardd, SpringBoard 및 기본 앱)가 구동됩니다.

> [!WARNING]
> 본 프로젝트는 하드웨어 브링업(bring-up) 목적의 실험적 연구 프로젝트입니다. 일상용 운영체제가 아닙니다.
> iOS는 기기의 `userdata` 파티션에 설치되므로 **기존 안드로이드 데이터가 완전히 포맷**됩니다. 필수 데이터는 반드시 사전에 백업하십시오.

---

## 지원 기기 사양 (LG V30 / joan)

| 항목 | 상세 스펙 |
| --- | --- |
| **타겟 기기** | LG V30 / V30+ / V30 ThinQ (한국 모델: LGM-V300S, LGM-V300K, LGM-V300L) |
| **코드네임** | `joan` |
| **SoC / AP** | Qualcomm Snapdragon 835 (MSM8998) |
| **CPU** | 옥타코어 Kryo 280 (4x Silver Cortex-A53 1.9GHz + 4x Gold Cortex-A73 2.45GHz), ARMv8.0-A |
| **GPU** | Adreno 540 (소프트웨어 CPU 렌더링 구동) |
| **RAM** | 4GB LPDDR4x (High-bank: `0x100000000`, 크기 ~1.95 GiB) |
| **스토리지** | 64GB / 128GB UFS 2.1 (`ufshc@1da4000`, 베이스 `0x01da4000`) |
| **디스플레이** | 6.0인치 18:9 P-OLED (2880 × 1440 QHD+, 538 ppi) |
| **프레임버퍼** | `cont_splash_mem`: `0x9d400000` (1440×2880, Stride: 5760 bytes) |
| **인터럽트 (GIC)** | ARM GICv3 (GICD: `0x17a00000`, GICR: `0x17b00000`, Timer INTID: 19) |
| **전원 관리** | PSHOLD: `0x010ac000`, IMEM restart_reason: `0x146bf65c` |
| **타겟 ID** | iPhone X (`iPhone10,3` / `D22AP`) |

---

## 부팅 구조 (Boot Architecture)

```
LG ABL (WTF Exploit으로 언락된 부트로더 + fastboot)
  -> fastboot boot shim-boot.img                  (임시 부팅: 부트 파티션을 영구 변조하지 않음)
     -> shim: LG V30 MMU 설정, 실시간 FDT 파싱, 램디스크에서 페이로드 로드
        -> XNU Mach-O + 생성된 Apple Device Tree (ADT) + boot-args
           -> XNU -> MSM8998 UFS 2.1 드라이버 -> userdata의 HFS+ 루트 볼륨 마운트
              -> dyld + shared cache -> launchd -> 백그라운드 데몬 -> backboardd + SpringBoard
```

---

## LG V30에서 직접 진행하는 절차

### 0. LG V30 부트로더 언락 및 백업 (중요)

LG전자의 공식 언락 서비스가 2021년 말 종료되었기 때문에, 한국판 LG V30(V300S/K/L)은 XDA의 **WTF (Whatever To Fastboot / Frank_Script)** 익스플로잇을 통해 언락해야 합니다.

1. **EDL / 9008 모드에서 파티션 전체 덤프**:
   - QPST / QFIL을 사용하여 `persist`, `modemst1`, `modemst2`, `fsg`, `fsc`, `boot`, `recovery`, `laf` 등을 반드시 PC에 백업합니다.
2. **WTF 익스플로잇 적용**:
   - 취약점이 있는 엔지니어링 `abl`을 주입하여 `fastboot` 모드를 활성화하고, `fastboot oem unlock`으로 부트로더를 언락합니다.
3. **순정 boot.img에서 DTB 추출**:
   ```sh
   python3 tools/unpack_bootv2.py backup/boot.img dtb/boot_unpacked
   # 추출된 dtb: dtb/boot_unpacked/dtb
   ```

---

### 1. XNU 커널 빌드

GitHub Actions 워크플로(`.github/workflows/xnu.yml`)를 사용하여 macOS 14 환경에서 크로스 컴파일합니다:

```sh
# 본인 리포지토리 포크 후 GitHub CLI로 실행
gh workflow run xnu.yml -R YOUR_ID/ios-joan
gh run download RUN_ID -R YOUR_ID/ios-joan -n xnu-kernel -D xnu/out
```

---

### 2. iOS 16 루트 파일시스템 생성

Apple 서버에서 iPhone X (iPhone10,3) iOS 16.7.16 (20H392) 순정 IPSW를 다운로드합니다. (Linux PC에서 `apfs-fuse`, `hfsprogs`, `android-sdk-libsparse-utils` 필요)

```sh
# 1. IPSW 내부의 OS.dmg, SystemOS.dmg, AppOS.dmg 마운트 및 통합 HFS+ 생성
tools/mkiosroot.sh OS.dmg SystemOS.dmg AppOS.dmg ios16-root.img 16G
sudo fsck.hfsplus -fy ios16-root.img

# 2. V30 환경에 맞춘 유저랜드 트윅 적용 (Setup 건너뛰기, 데몬 비활성화 등)
sudo mount -t hfsplus -o loop,force ios16-root.img /mnt/iosroot
sudo python3 tools/sweet-root-tweaks.py /mnt/iosroot
sudo umount /mnt/iosroot

# 3. userdata 플래시용 sparse 이미지 변환
img2simg ios16-root.img ios16-root.simg
```

---

### 3. V30 전용 ADT 및 부트 이미지(shim-boot.img) 제작

`aarch64-linux-gnu-gcc` 및 `mkbootimg`가 필요합니다.

```sh
# 1. LG V30 MSM8998용 Apple Device Tree (ADT) 빌드
python3 tools/mkadt.py shim/out/joan.adt --highmem

# 2. 페이로드 패킹 (커널 + ADT + boot-args)
python3 tools/mkpayload.py xnu/out/kernel.development.sweet shim/out/joan.adt shim/out/payload.bin \
    --cmdline 'debug=0xc serial=3 cpus=4 keepsyms=1 -enable_kprintf_spam -noprogress rd=ufsroot0 unentitled_ios_sim_launch=1 ignition_level=1 wdt_test=no_user_checkin ufsrw=1 rootrw=1 launchd_unsecure_cache=1 wdt=-1 sweetfb_noconsole=1 sweetfb_hz=30 sweettouch=0 sweetkeys=0'

# 3. LG V30 bootimg 헤더(base 0, kernel 0x8000, ramdisk 0x02000000, tags 0x01e00000)로 shim 패킹
shim/build.sh ../shim/out/payload.bin      # -> shim/out/shim-boot.img 생성
```

> [!TIP]
> **초기 브링업 추천 부트 플래그**:
> - `cpus=1` 또는 `cpus=4`: 먼저 Little 코어(Silver 4개)로 안정적 부팅을 확인한 후 `cpus=8`로 확장하십시오.
> - `sweettouch=0 sweetkeys=0`: 초기 단계에서는 부트로더 콘솔 및 프레임버퍼 화면 표시에 집중하기 위해 터치/버튼 드라이버를 꺼둡니다.

---

### 4. userdata 플래시 및 부팅

전원을 끄고 `볼륨 하(-) + 전원` 버튼으로 fastboot 모드에 진입한 뒤 PC와 연결합니다:

```sh
# userdata 파티션에 iOS 루트 파일시스템 플래시 (기존 데이터 초기화)
fastboot -S 512M flash userdata ios16-root.simg

# shim 부트 이미지 일시 부팅 (boot 파티션을 덮어쓰지 않고 메모리로 직접 로드)
fastboot boot shim/out/shim-boot.img
```

첫 부팅 시 Apple 로고에서 약 3~4분간 초기 파일시스템 설정을 거친 후 잠금 화면이 나타납니다.

---

### 5. 커널 로그 확인 (디버깅)

LG V30용 TWRP 리커버리를 통해 `userdata` 파티션 끝의 4 MiB 로그 링 버퍼를 덤프할 수 있습니다:

```sh
fastboot boot twrp-joan.img
tools/sweet-log-pull.sh logs/v30_boot.txt
```

---

## 리포지토리 구성

| 경로 | 설명 |
| --- | --- |
| `shim/` | LG V30 전용 베어메탈 부트 심(C + Asm) 및 안드로이드 부트 이미지 생성 스크립트 |
| `tools/mkadt.py` | LG V30 (MSM8998)의 하드웨어 주소(GIC, UFS, RAM, FB)를 반영한 ADT 빌더 |
| `tools/mkpayload.py` | 커널과 ADT, 부트 플래그를 결합하는 페이로드 생성기 |
| `tools/mkiosroot.sh` | 순정 iPhone X IPSW로부터 iOS 16 HFS+ 루트 이미지를 추출/생성 |
| `tools/sweet-root-tweaks.py` | 비활성 하드웨어 크래시 방지 및 브링업 최적화 유저랜드 패치 |
| `tools/sweet-log-pull.sh` | 리커버리 ADB를 통한 커널 로그 추출 스크립트 |
| `xnu/patches/` | MSM8998 ARMv8.0-A 호환, GICv3, 1440x2880 디스플레이, UFS 드라이버가 포함된 XNU 패치 모음 |

---

## 하드웨어 매핑 요약 (MSM8998 vs SM7150)

| 모듈 | Redmi Note 10 Pro (sweet) | LG V30 (joan, MSM8998) |
| --- | --- | --- |
| **CPU 아키텍처** | ARMv8.2-A (Kryo 470) | **ARMv8.0-A** (Kryo 280) |
| **MPIDR 구조** | 단일 클러스터 (`Aff1 = core`) | **Big.LITTLE** (`0x000..0x003`, `0x100..0x103`) |
| **UFS 컨트롤러 베이스** | `0x01d84000` | **`0x01da4000`** |
| **GICv3 재배포기(GICR)** | `0x17a60000` | **`0x17b00000`** |
| **프레임버퍼 (cont_splash)** | `0x9c000000` (1080×2400) | **`0x9d400000` (1440×2880)** |
| **PSHOLD (재부팅 제어)** | `0x0c264000` | **`0x010ac000`** |
| **IMEM 재부팅 사유 레지스터** | `0x146aa65c` | **`0x146bf65c`** |
| **Bootimg Ramdisk Offset** | `0x01000000` | **`0x02000000`** |
| **Bootimg Tags Offset** | `0x00000100` | **`0x01e00000`** |
