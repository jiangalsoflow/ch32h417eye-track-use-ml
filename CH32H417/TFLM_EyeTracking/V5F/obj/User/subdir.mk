################################################################################
# MRS Version: 2.4.0
# Automatically-generated file. Do not edit!
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
C_SRCS += \
../User/ch32h417_it.c \
../User/main.c \
../User/system_ch32h417.c 

C_DEPS += \
./User/ch32h417_it.d \
./User/main.d \
./User/system_ch32h417.d 

CC_SRCS += \
../User/eye_tracking_inference.cc 

CC_DEPS += \
./User/eye_tracking_inference.d 

OBJS += \
./User/ch32h417_it.o \
./User/eye_tracking_inference.o \
./User/main.o \
./User/system_ch32h417.o 

DIR_OBJS += \
./User/*.o \

DIR_DEPS += \
./User/*.d \

DIR_EXPANDS += \
./User/*.253r.expand \


# Each subdirectory must supply rules for building sources it contributes
User/%.o: ../User/%.c
	@	riscv-wch-elf-gcc -march=rv32imac_zba_zbb_zbc_zbs_xw -mabi=ilp32 -msmall-data-limit=8 -msave-restore -fmax-errors=20 -Os -fmessage-length=0 -fsigned-char -ffunction-sections -fdata-sections -fno-common -Wunused -Wuninitialized -g -DCore_V5F -I"c:/Users/13228/Desktop/Match/CH32H417/sdk_ch32h417/SRC/Debug" -I"c:/Users/13228/Desktop/Match/CH32H417/sdk_ch32h417/SRC/Core" -I"c:/Users/13228/Desktop/Match/CH32H417/TFLM_EyeTracking/V5F/User" -I"c:/Users/13228/Desktop/Match/CH32H417/sdk_ch32h417/SRC/Peripheral/inc" -I"c:/Users/13228/Desktop/Match/CH32H417/TFLM_EyeTracking/V5F/User/tflm" -I"c:/Users/13228/Desktop/Match/CH32H417/TFLM_EyeTracking/V5F/User/tflm/third_party/kissfft" -I"c:/Users/13228/Desktop/Match/CH32H417/TFLM_EyeTracking/V5F/User/tflm/third_party/flatbuffers/include" -I"c:/Users/13228/Desktop/Match/CH32H417/TFLM_EyeTracking/V5F/User/tflm/third_party/gemmlowp" -I"c:/Users/13228/Desktop/Match/CH32H417/TFLM_EyeTracking/V5F/User/tflm/third_party/ruy" -std=gnu99 -MMD -MP -MF"$(@:%.o=%.d)" -MT"$(@)" -c -o "$@" "$<"

User/%.o: ../User/%.cc
	@	riscv-wch-elf-g++ -march=rv32imac_zba_zbb_zbc_zbs_xw -mabi=ilp32 -msmall-data-limit=8 -msave-restore -fmax-errors=20 -Os -fmessage-length=0 -fsigned-char -ffunction-sections -fdata-sections -fno-common -Wunused -Wuninitialized -g -I"c:/Users/13228/Desktop/Match/CH32H417/TFLM_EyeTracking/V5F/User/tflm" -I"c:/Users/13228/Desktop/Match/CH32H417/TFLM_EyeTracking/V5F/User/tflm/third_party/kissfft" -I"c:/Users/13228/Desktop/Match/CH32H417/TFLM_EyeTracking/V5F/User/tflm/third_party/flatbuffers/include" -I"c:/Users/13228/Desktop/Match/CH32H417/TFLM_EyeTracking/V5F/User/tflm/third_party/gemmlowp" -I"c:/Users/13228/Desktop/Match/CH32H417/TFLM_EyeTracking/V5F/User/tflm/third_party/ruy" -I"c:/Users/13228/Desktop/Match/CH32H417/sdk_ch32h417/SRC/Debug" -I"c:/Users/13228/Desktop/Match/CH32H417/sdk_ch32h417/SRC/Core" -I"c:/Users/13228/Desktop/Match/CH32H417/TFLM_EyeTracking/V5F/User" -I"c:/Users/13228/Desktop/Match/CH32H417/sdk_ch32h417/SRC/Peripheral/inc" -std=gnu++11 -fabi-version=0 -MMD -MP -MF"$(@:%.o=%.d)" -MT"$(@)" -c -o "$@" "$<"

