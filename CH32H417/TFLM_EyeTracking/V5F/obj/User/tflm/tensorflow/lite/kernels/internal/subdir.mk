################################################################################
# MRS Version: 2.4.0
# Automatically-generated file. Do not edit!
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
CC_SRCS += \
../User/tflm/tensorflow/lite/kernels/internal/common.cc \
../User/tflm/tensorflow/lite/kernels/internal/portable_tensor_utils.cc \
../User/tflm/tensorflow/lite/kernels/internal/quantization_util.cc \
../User/tflm/tensorflow/lite/kernels/internal/runtime_shape.cc \
../User/tflm/tensorflow/lite/kernels/internal/tensor_ctypes.cc \
../User/tflm/tensorflow/lite/kernels/internal/tensor_utils.cc 

CC_DEPS += \
./User/tflm/tensorflow/lite/kernels/internal/common.d \
./User/tflm/tensorflow/lite/kernels/internal/portable_tensor_utils.d \
./User/tflm/tensorflow/lite/kernels/internal/quantization_util.d \
./User/tflm/tensorflow/lite/kernels/internal/runtime_shape.d \
./User/tflm/tensorflow/lite/kernels/internal/tensor_ctypes.d \
./User/tflm/tensorflow/lite/kernels/internal/tensor_utils.d 

OBJS += \
./User/tflm/tensorflow/lite/kernels/internal/common.o \
./User/tflm/tensorflow/lite/kernels/internal/portable_tensor_utils.o \
./User/tflm/tensorflow/lite/kernels/internal/quantization_util.o \
./User/tflm/tensorflow/lite/kernels/internal/runtime_shape.o \
./User/tflm/tensorflow/lite/kernels/internal/tensor_ctypes.o \
./User/tflm/tensorflow/lite/kernels/internal/tensor_utils.o 

DIR_OBJS += \
./User/tflm/tensorflow/lite/kernels/internal/*.o \

DIR_DEPS += \
./User/tflm/tensorflow/lite/kernels/internal/*.d \

DIR_EXPANDS += \
./User/tflm/tensorflow/lite/kernels/internal/*.253r.expand \


# Each subdirectory must supply rules for building sources it contributes
User/tflm/tensorflow/lite/kernels/internal/%.o: ../User/tflm/tensorflow/lite/kernels/internal/%.cc
	@	riscv-wch-elf-g++ -march=rv32imac_zba_zbb_zbc_zbs_xw -mabi=ilp32 -msmall-data-limit=8 -msave-restore -fmax-errors=20 -Os -fmessage-length=0 -fsigned-char -ffunction-sections -fdata-sections -fno-common -Wunused -Wuninitialized -g -I"c:/Users/13228/Desktop/Match/CH32H417/TFLM_EyeTracking/V5F/User/tflm" -I"c:/Users/13228/Desktop/Match/CH32H417/TFLM_EyeTracking/V5F/User/tflm/third_party/kissfft" -I"c:/Users/13228/Desktop/Match/CH32H417/TFLM_EyeTracking/V5F/User/tflm/third_party/flatbuffers/include" -I"c:/Users/13228/Desktop/Match/CH32H417/TFLM_EyeTracking/V5F/User/tflm/third_party/gemmlowp" -I"c:/Users/13228/Desktop/Match/CH32H417/TFLM_EyeTracking/V5F/User/tflm/third_party/ruy" -I"c:/Users/13228/Desktop/Match/CH32H417/sdk_ch32h417/SRC/Debug" -I"c:/Users/13228/Desktop/Match/CH32H417/sdk_ch32h417/SRC/Core" -I"c:/Users/13228/Desktop/Match/CH32H417/TFLM_EyeTracking/V5F/User" -I"c:/Users/13228/Desktop/Match/CH32H417/sdk_ch32h417/SRC/Peripheral/inc" -std=gnu++11 -fabi-version=0 -MMD -MP -MF"$(@:%.o=%.d)" -MT"$(@)" -c -o "$@" "$<"

