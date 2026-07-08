################################################################################
# MRS Version: 2.4.0
# Automatically-generated file. Do not edit!
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
C_SRCS += \
e:/dvp-uart/Match/CH32H417/sdk_ch32h417/SRC/Core/core_riscv.c 

C_DEPS += \
./Core/core_riscv.d 

OBJS += \
./Core/core_riscv.o 

DIR_OBJS += \
./Core/*.o \

DIR_DEPS += \
./Core/*.d \

DIR_EXPANDS += \
./Core/*.253r.expand \


# Each subdirectory must supply rules for building sources it contributes
Core/core_riscv.o: e:/dvp-uart/Match/CH32H417/sdk_ch32h417/SRC/Core/core_riscv.c
	@	riscv-wch-elf-gcc -march=rv32imac_zba_zbb_zbc_zbs_xw -mabi=ilp32 -msmall-data-limit=8 -msave-restore -fmax-errors=20 -Os -fmessage-length=0 -fsigned-char -ffunction-sections -fdata-sections -fno-common -Wunused -Wuninitialized -g -DCore_V5F -I"e:/dvp-uart/Match/CH32H417/sdk_ch32h417/SRC/Debug" -I"e:/dvp-uart/Match/CH32H417/sdk_ch32h417/SRC/Core" -I"e:/dvp-uart/Match/CH32H417/sdk_ch32h417/DVP/DVP_UART_Test5/V5F/User" -I"e:/dvp-uart/Match/CH32H417/sdk_ch32h417/SRC/Peripheral/inc" -I"e:/dvp-uart/Match/CH32H417/sdk_ch32h417/DVP/DVP_UART_Test5/Common" -std=gnu99 -MMD -MP -MF"$(@:%.o=%.d)" -MT"$(@)" -c -o "$@" "$<"

