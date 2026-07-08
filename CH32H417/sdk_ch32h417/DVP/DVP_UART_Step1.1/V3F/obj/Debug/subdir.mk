################################################################################
# MRS Version: 2.4.0
# Automatically-generated file. Do not edit!
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
C_SRCS += \
e:/dvp-uart/Match/CH32H417/sdk_ch32h417/SRC/Debug/debug.c 

C_DEPS += \
./Debug/debug.d 

OBJS += \
./Debug/debug.o 

DIR_OBJS += \
./Debug/*.o \

DIR_DEPS += \
./Debug/*.d \

DIR_EXPANDS += \
./Debug/*.253r.expand \


# Each subdirectory must supply rules for building sources it contributes
Debug/debug.o: e:/dvp-uart/Match/CH32H417/sdk_ch32h417/SRC/Debug/debug.c
	@	riscv-wch-elf-gcc -march=rv32imac_zba_zbb_zbc_zbs_xw -mabi=ilp32 -msmall-data-limit=8 -msave-restore -fmax-errors=20 -Os -fmessage-length=0 -fsigned-char -ffunction-sections -fdata-sections -fno-common -Wunused -Wuninitialized -g -DCore_V3F -I"e:/dvp-uart/Match/CH32H417/sdk_ch32h417/SRC/Debug" -I"e:/dvp-uart/Match/CH32H417/sdk_ch32h417/SRC/Core" -I"e:/dvp-uart/Match/CH32H417/sdk_ch32h417/DVP/DVP_UART_Step1.1/V3F/User" -I"e:/dvp-uart/Match/CH32H417/sdk_ch32h417/SRC/Peripheral/inc" -I"e:/dvp-uart/Match/CH32H417/sdk_ch32h417/DVP/DVP_UART_Step1.1/Common" -std=gnu99 -MMD -MP -MF"$(@:%.o=%.d)" -MT"$(@)" -c -o "$@" "$<"

