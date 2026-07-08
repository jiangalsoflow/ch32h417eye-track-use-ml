################################################################################
# MRS Version: 2.4.0
# Automatically-generated file. Do not edit!
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
C_SRCS += \
e:/dvp-uart/Match/CH32H417/sdk_ch32h417/DVP/DVP_UART_Step4/Common/hardware.c \
e:/dvp-uart/Match/CH32H417/sdk_ch32h417/DVP/DVP_UART_Step4/Common/inference.c \
e:/dvp-uart/Match/CH32H417/sdk_ch32h417/DVP/DVP_UART_Step4/Common/jpeg_dec.c \
e:/dvp-uart/Match/CH32H417/sdk_ch32h417/DVP/DVP_UART_Step4/Common/ov2640.c \
e:/dvp-uart/Match/CH32H417/sdk_ch32h417/DVP/DVP_UART_Step4/Common/weights_simple.c 

C_DEPS += \
./Common/hardware.d \
./Common/inference.d \
./Common/jpeg_dec.d \
./Common/ov2640.d \
./Common/weights_simple.d 

OBJS += \
./Common/hardware.o \
./Common/inference.o \
./Common/jpeg_dec.o \
./Common/ov2640.o \
./Common/weights_simple.o 

DIR_OBJS += \
./Common/*.o \

DIR_DEPS += \
./Common/*.d \

DIR_EXPANDS += \
./Common/*.253r.expand \


# Each subdirectory must supply rules for building sources it contributes
Common/hardware.o: e:/dvp-uart/Match/CH32H417/sdk_ch32h417/DVP/DVP_UART_Step4/Common/hardware.c
	@	riscv-wch-elf-gcc -march=rv32imac_zba_zbb_zbc_zbs_xw -mabi=ilp32 -msmall-data-limit=8 -msave-restore -fmax-errors=20 -Os -fmessage-length=0 -fsigned-char -ffunction-sections -fdata-sections -fno-common -Wunused -Wuninitialized -g -DCore_V5F -I"e:/dvp-uart/Match/CH32H417/sdk_ch32h417/SRC/Debug" -I"e:/dvp-uart/Match/CH32H417/sdk_ch32h417/SRC/Core" -I"e:/dvp-uart/Match/CH32H417/sdk_ch32h417/DVP/DVP_UART_Step4/V5F/User" -I"e:/dvp-uart/Match/CH32H417/sdk_ch32h417/SRC/Peripheral/inc" -I"e:/dvp-uart/Match/CH32H417/sdk_ch32h417/DVP/DVP_UART_Step4/Common" -std=gnu99 -MMD -MP -MF"$(@:%.o=%.d)" -MT"$(@)" -c -o "$@" "$<"
Common/inference.o: e:/dvp-uart/Match/CH32H417/sdk_ch32h417/DVP/DVP_UART_Step4/Common/inference.c
	@	riscv-wch-elf-gcc -march=rv32imac_zba_zbb_zbc_zbs_xw -mabi=ilp32 -msmall-data-limit=8 -msave-restore -fmax-errors=20 -Os -fmessage-length=0 -fsigned-char -ffunction-sections -fdata-sections -fno-common -Wunused -Wuninitialized -g -DCore_V5F -I"e:/dvp-uart/Match/CH32H417/sdk_ch32h417/SRC/Debug" -I"e:/dvp-uart/Match/CH32H417/sdk_ch32h417/SRC/Core" -I"e:/dvp-uart/Match/CH32H417/sdk_ch32h417/DVP/DVP_UART_Step4/V5F/User" -I"e:/dvp-uart/Match/CH32H417/sdk_ch32h417/SRC/Peripheral/inc" -I"e:/dvp-uart/Match/CH32H417/sdk_ch32h417/DVP/DVP_UART_Step4/Common" -std=gnu99 -MMD -MP -MF"$(@:%.o=%.d)" -MT"$(@)" -c -o "$@" "$<"
Common/jpeg_dec.o: e:/dvp-uart/Match/CH32H417/sdk_ch32h417/DVP/DVP_UART_Step4/Common/jpeg_dec.c
	@	riscv-wch-elf-gcc -march=rv32imac_zba_zbb_zbc_zbs_xw -mabi=ilp32 -msmall-data-limit=8 -msave-restore -fmax-errors=20 -Os -fmessage-length=0 -fsigned-char -ffunction-sections -fdata-sections -fno-common -Wunused -Wuninitialized -g -DCore_V5F -I"e:/dvp-uart/Match/CH32H417/sdk_ch32h417/SRC/Debug" -I"e:/dvp-uart/Match/CH32H417/sdk_ch32h417/SRC/Core" -I"e:/dvp-uart/Match/CH32H417/sdk_ch32h417/DVP/DVP_UART_Step4/V5F/User" -I"e:/dvp-uart/Match/CH32H417/sdk_ch32h417/SRC/Peripheral/inc" -I"e:/dvp-uart/Match/CH32H417/sdk_ch32h417/DVP/DVP_UART_Step4/Common" -std=gnu99 -MMD -MP -MF"$(@:%.o=%.d)" -MT"$(@)" -c -o "$@" "$<"
Common/ov2640.o: e:/dvp-uart/Match/CH32H417/sdk_ch32h417/DVP/DVP_UART_Step4/Common/ov2640.c
	@	riscv-wch-elf-gcc -march=rv32imac_zba_zbb_zbc_zbs_xw -mabi=ilp32 -msmall-data-limit=8 -msave-restore -fmax-errors=20 -Os -fmessage-length=0 -fsigned-char -ffunction-sections -fdata-sections -fno-common -Wunused -Wuninitialized -g -DCore_V5F -I"e:/dvp-uart/Match/CH32H417/sdk_ch32h417/SRC/Debug" -I"e:/dvp-uart/Match/CH32H417/sdk_ch32h417/SRC/Core" -I"e:/dvp-uart/Match/CH32H417/sdk_ch32h417/DVP/DVP_UART_Step4/V5F/User" -I"e:/dvp-uart/Match/CH32H417/sdk_ch32h417/SRC/Peripheral/inc" -I"e:/dvp-uart/Match/CH32H417/sdk_ch32h417/DVP/DVP_UART_Step4/Common" -std=gnu99 -MMD -MP -MF"$(@:%.o=%.d)" -MT"$(@)" -c -o "$@" "$<"
Common/weights_simple.o: e:/dvp-uart/Match/CH32H417/sdk_ch32h417/DVP/DVP_UART_Step4/Common/weights_simple.c
	@	riscv-wch-elf-gcc -march=rv32imac_zba_zbb_zbc_zbs_xw -mabi=ilp32 -msmall-data-limit=8 -msave-restore -fmax-errors=20 -Os -fmessage-length=0 -fsigned-char -ffunction-sections -fdata-sections -fno-common -Wunused -Wuninitialized -g -DCore_V5F -I"e:/dvp-uart/Match/CH32H417/sdk_ch32h417/SRC/Debug" -I"e:/dvp-uart/Match/CH32H417/sdk_ch32h417/SRC/Core" -I"e:/dvp-uart/Match/CH32H417/sdk_ch32h417/DVP/DVP_UART_Step4/V5F/User" -I"e:/dvp-uart/Match/CH32H417/sdk_ch32h417/SRC/Peripheral/inc" -I"e:/dvp-uart/Match/CH32H417/sdk_ch32h417/DVP/DVP_UART_Step4/Common" -std=gnu99 -MMD -MP -MF"$(@:%.o=%.d)" -MT"$(@)" -c -o "$@" "$<"

