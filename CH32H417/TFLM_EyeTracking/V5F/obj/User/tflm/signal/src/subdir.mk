################################################################################
# MRS Version: 2.4.0
# Automatically-generated file. Do not edit!
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
CC_SRCS += \
../User/tflm/signal/src/circular_buffer.cc \
../User/tflm/signal/src/energy.cc \
../User/tflm/signal/src/fft_auto_scale.cc \
../User/tflm/signal/src/filter_bank.cc \
../User/tflm/signal/src/filter_bank_log.cc \
../User/tflm/signal/src/filter_bank_spectral_subtraction.cc \
../User/tflm/signal/src/filter_bank_square_root.cc \
../User/tflm/signal/src/irfft_float.cc \
../User/tflm/signal/src/irfft_int16.cc \
../User/tflm/signal/src/irfft_int32.cc \
../User/tflm/signal/src/log.cc \
../User/tflm/signal/src/max_abs.cc \
../User/tflm/signal/src/msb_32.cc \
../User/tflm/signal/src/msb_64.cc \
../User/tflm/signal/src/overlap_add.cc \
../User/tflm/signal/src/pcan_argc_fixed.cc \
../User/tflm/signal/src/rfft_float.cc \
../User/tflm/signal/src/rfft_int16.cc \
../User/tflm/signal/src/rfft_int32.cc \
../User/tflm/signal/src/square_root_32.cc \
../User/tflm/signal/src/square_root_64.cc \
../User/tflm/signal/src/window.cc 

CC_DEPS += \
./User/tflm/signal/src/circular_buffer.d \
./User/tflm/signal/src/energy.d \
./User/tflm/signal/src/fft_auto_scale.d \
./User/tflm/signal/src/filter_bank.d \
./User/tflm/signal/src/filter_bank_log.d \
./User/tflm/signal/src/filter_bank_spectral_subtraction.d \
./User/tflm/signal/src/filter_bank_square_root.d \
./User/tflm/signal/src/irfft_float.d \
./User/tflm/signal/src/irfft_int16.d \
./User/tflm/signal/src/irfft_int32.d \
./User/tflm/signal/src/log.d \
./User/tflm/signal/src/max_abs.d \
./User/tflm/signal/src/msb_32.d \
./User/tflm/signal/src/msb_64.d \
./User/tflm/signal/src/overlap_add.d \
./User/tflm/signal/src/pcan_argc_fixed.d \
./User/tflm/signal/src/rfft_float.d \
./User/tflm/signal/src/rfft_int16.d \
./User/tflm/signal/src/rfft_int32.d \
./User/tflm/signal/src/square_root_32.d \
./User/tflm/signal/src/square_root_64.d \
./User/tflm/signal/src/window.d 

OBJS += \
./User/tflm/signal/src/circular_buffer.o \
./User/tflm/signal/src/energy.o \
./User/tflm/signal/src/fft_auto_scale.o \
./User/tflm/signal/src/filter_bank.o \
./User/tflm/signal/src/filter_bank_log.o \
./User/tflm/signal/src/filter_bank_spectral_subtraction.o \
./User/tflm/signal/src/filter_bank_square_root.o \
./User/tflm/signal/src/irfft_float.o \
./User/tflm/signal/src/irfft_int16.o \
./User/tflm/signal/src/irfft_int32.o \
./User/tflm/signal/src/log.o \
./User/tflm/signal/src/max_abs.o \
./User/tflm/signal/src/msb_32.o \
./User/tflm/signal/src/msb_64.o \
./User/tflm/signal/src/overlap_add.o \
./User/tflm/signal/src/pcan_argc_fixed.o \
./User/tflm/signal/src/rfft_float.o \
./User/tflm/signal/src/rfft_int16.o \
./User/tflm/signal/src/rfft_int32.o \
./User/tflm/signal/src/square_root_32.o \
./User/tflm/signal/src/square_root_64.o \
./User/tflm/signal/src/window.o 

DIR_OBJS += \
./User/tflm/signal/src/*.o \

DIR_DEPS += \
./User/tflm/signal/src/*.d \

DIR_EXPANDS += \
./User/tflm/signal/src/*.253r.expand \


# Each subdirectory must supply rules for building sources it contributes
User/tflm/signal/src/%.o: ../User/tflm/signal/src/%.cc
	@	riscv-wch-elf-g++ -march=rv32imac_zba_zbb_zbc_zbs_xw -mabi=ilp32 -msmall-data-limit=8 -msave-restore -fmax-errors=20 -Os -fmessage-length=0 -fsigned-char -ffunction-sections -fdata-sections -fno-common -Wunused -Wuninitialized -g -I"c:/Users/13228/Desktop/Match/CH32H417/TFLM_EyeTracking/V5F/User/tflm" -I"c:/Users/13228/Desktop/Match/CH32H417/TFLM_EyeTracking/V5F/User/tflm/third_party/kissfft" -I"c:/Users/13228/Desktop/Match/CH32H417/TFLM_EyeTracking/V5F/User/tflm/third_party/flatbuffers/include" -I"c:/Users/13228/Desktop/Match/CH32H417/TFLM_EyeTracking/V5F/User/tflm/third_party/gemmlowp" -I"c:/Users/13228/Desktop/Match/CH32H417/TFLM_EyeTracking/V5F/User/tflm/third_party/ruy" -I"c:/Users/13228/Desktop/Match/CH32H417/sdk_ch32h417/SRC/Debug" -I"c:/Users/13228/Desktop/Match/CH32H417/sdk_ch32h417/SRC/Core" -I"c:/Users/13228/Desktop/Match/CH32H417/TFLM_EyeTracking/V5F/User" -I"c:/Users/13228/Desktop/Match/CH32H417/sdk_ch32h417/SRC/Peripheral/inc" -std=gnu++11 -fabi-version=0 -MMD -MP -MF"$(@:%.o=%.d)" -MT"$(@)" -c -o "$@" "$<"

