################################################################################
# MRS Version: 2.4.0
# Automatically-generated file. Do not edit!
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
CC_SRCS += \
../User/tflm/signal/src/kiss_fft_wrappers/kiss_fft_float.cc \
../User/tflm/signal/src/kiss_fft_wrappers/kiss_fft_int16.cc \
../User/tflm/signal/src/kiss_fft_wrappers/kiss_fft_int32.cc 

CC_DEPS += \
./User/tflm/signal/src/kiss_fft_wrappers/kiss_fft_float.d \
./User/tflm/signal/src/kiss_fft_wrappers/kiss_fft_int16.d \
./User/tflm/signal/src/kiss_fft_wrappers/kiss_fft_int32.d 

OBJS += \
./User/tflm/signal/src/kiss_fft_wrappers/kiss_fft_float.o \
./User/tflm/signal/src/kiss_fft_wrappers/kiss_fft_int16.o \
./User/tflm/signal/src/kiss_fft_wrappers/kiss_fft_int32.o 

DIR_OBJS += \
./User/tflm/signal/src/kiss_fft_wrappers/*.o \

DIR_DEPS += \
./User/tflm/signal/src/kiss_fft_wrappers/*.d \

DIR_EXPANDS += \
./User/tflm/signal/src/kiss_fft_wrappers/*.253r.expand \


# Each subdirectory must supply rules for building sources it contributes
User/tflm/signal/src/kiss_fft_wrappers/%.o: ../User/tflm/signal/src/kiss_fft_wrappers/%.cc
	@	riscv-wch-elf-g++ -march=rv32imac_zba_zbb_zbc_zbs_xw -mabi=ilp32 -msmall-data-limit=8 -msave-restore -fmax-errors=20 -Os -fmessage-length=0 -fsigned-char -ffunction-sections -fdata-sections -fno-common -Wunused -Wuninitialized -g -I"c:/Users/13228/Desktop/Match/CH32H417/TFLM_EyeTracking/V5F/User/tflm" -I"c:/Users/13228/Desktop/Match/CH32H417/TFLM_EyeTracking/V5F/User/tflm/third_party/kissfft" -I"c:/Users/13228/Desktop/Match/CH32H417/TFLM_EyeTracking/V5F/User/tflm/third_party/flatbuffers/include" -I"c:/Users/13228/Desktop/Match/CH32H417/TFLM_EyeTracking/V5F/User/tflm/third_party/gemmlowp" -I"c:/Users/13228/Desktop/Match/CH32H417/TFLM_EyeTracking/V5F/User/tflm/third_party/ruy" -I"c:/Users/13228/Desktop/Match/CH32H417/sdk_ch32h417/SRC/Debug" -I"c:/Users/13228/Desktop/Match/CH32H417/sdk_ch32h417/SRC/Core" -I"c:/Users/13228/Desktop/Match/CH32H417/TFLM_EyeTracking/V5F/User" -I"c:/Users/13228/Desktop/Match/CH32H417/sdk_ch32h417/SRC/Peripheral/inc" -std=gnu++11 -fabi-version=0 -MMD -MP -MF"$(@:%.o=%.d)" -MT"$(@)" -c -o "$@" "$<"

