// Press Right -- DE10-Lite Top Module  (Challenge 4)
//
// A 10ms counter displayed on HEX3:HEX0.
//   KEY[0] starts the counter.
//   KEY[0] again stops it and sends the value ("NNNN\n") to the ESP32 via UART.
//   The ESP32 plays a victory buzzer if the stopped value is 1000 ± 10.
//
// Displays:
//   HEX3:HEX0 = counter (0000-9999, 4-digit decimal)
//   HEX4, HEX5 = blank
//   LEDR[9:0]  = bar-graph: more LEDs = closer to 1000
//
// UART TX: GPIO[1] (JP1 pin 2) → ESP32 GPIO17 (UART2 RX)  9600 8N1
// Reset  : SW[9] active-low

module press_right_top (
    input           MAX10_CLK1_50,
    input   [9:0]   SW,
    input   [1:0]   KEY,
    output  [9:0]   LEDR,
    output  [7:0]   HEX0, HEX1, HEX2, HEX3, HEX4, HEX5,
    inout   [35:0]  GPIO
);

    wire clk   = MAX10_CLK1_50;
    wire rst_n = SW[9];

    // GPIO[1] drives FPGA TX → ESP32; all others float
    wire fpga_tx_pin;
    assign GPIO[35:2] = 34'bz;
    assign GPIO[1]    = fpga_tx_pin;   // FPGA TX → ESP32 GPIO17
    assign GPIO[0]    = 1'bz;          // not used

    // ----------------------------------------------------------------
    // KEY[0] synchronizer, edge detector, and 20 ms debounce
    // ----------------------------------------------------------------
    logic key0_s1, key0_s2, key0_prev;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            key0_s1   <= 1'b1;
            key0_s2   <= 1'b1;
            key0_prev <= 1'b1;
        end else begin
            key0_s1   <= KEY[0];
            key0_s2   <= key0_s1;
            key0_prev <= key0_s2;
        end
    end

    wire key0_fall = key0_prev & ~key0_s2;   // falling edge = press

    logic [20:0] deb_cnt;
    logic        deb_ok;   // 1 → presses are accepted

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            deb_cnt <= '0;
            deb_ok  <= 1'b1;
        end else begin
            if (key0_fall && deb_ok) begin
                deb_cnt <= '0;
                deb_ok  <= 1'b0;
            end else if (!deb_ok) begin
                if (deb_cnt == 21'd1_000_000)   // 20 ms @ 50 MHz
                    deb_ok <= 1'b1;
                else
                    deb_cnt <= deb_cnt + 1;
            end
        end
    end

    wire key0_press = key0_fall & deb_ok;   // debounced, one-cycle pulse

    // ----------------------------------------------------------------
    // 10 ms tick  (50 MHz / 500 000 = 100 Hz)
    // ----------------------------------------------------------------
    logic [18:0] tick_cnt;
    logic        tick;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            tick_cnt <= '0;
            tick     <= 1'b0;
        end else begin
            if (tick_cnt == 19'd499_999) begin
                tick_cnt <= '0;
                tick     <= 1'b1;
            end else begin
                tick_cnt <= tick_cnt + 1;
                tick     <= 1'b0;
            end
        end
    end

    // ----------------------------------------------------------------
    // Counter  (BCD for display + binary for LED proximity)
    // ----------------------------------------------------------------
    logic [3:0] d3, d2, d1, d0;   // thousands, hundreds, tens, ones
    logic [13:0] count_bin;        // same value in binary (0 – 9999)

    // Latched values when counter is stopped
    logic [3:0]  d3s, d2s, d1s, d0s;
    logic [13:0] count_stop;

    // ----------------------------------------------------------------
    // Top-level state machine
    // ----------------------------------------------------------------
    typedef enum logic [2:0] {
        S_IDLE,      // counter = 0, waiting for first KEY[0]
        S_RUNNING,   // counting up every 10 ms
        S_SEND_PREP, // latch value, load TX buffer
        S_SENDING,   // streaming "NNNN\n" over UART
        S_DONE       // display frozen, waiting for KEY[0] to restart
    } state_t;

    state_t state;

    // UART TX control registers
    logic [7:0] send_buf [0:4];   // ASCII "NNNN\n"
    logic [2:0] send_idx;
    logic [7:0] tx_data_r;
    logic       tx_valid_r;
    wire        tx_busy;
    logic       tx_busy_d;

    // Falling edge of tx_busy = one byte just finished
    wire tx_done = tx_busy_d & ~tx_busy;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state      <= S_IDLE;
            d3 <= '0; d2 <= '0; d1 <= '0; d0 <= '0;
            count_bin  <= '0;
            d3s <= '0; d2s <= '0; d1s <= '0; d0s <= '0;
            count_stop <= '0;
            tx_data_r  <= '0;
            tx_valid_r <= 1'b0;
            tx_busy_d  <= 1'b0;
            send_idx   <= '0;
            send_buf[0] <= '0; send_buf[1] <= '0; send_buf[2] <= '0;
            send_buf[3] <= '0; send_buf[4] <= '0;
        end else begin
            tx_valid_r <= 1'b0;          // default: no TX pulse
            tx_busy_d  <= tx_busy;       // track tx_busy falling edge

            case (state)

                // ---- IDLE: show "0000", wait for start ----
                S_IDLE: begin
                    d3 <= '0; d2 <= '0; d1 <= '0; d0 <= '0;
                    count_bin <= '0;
                    if (key0_press) state <= S_RUNNING;
                end

                // ---- RUNNING: count up every 10 ms ----
                S_RUNNING: begin
                    if (key0_press) begin
                        // Stop — latch value and go to TX
                        d3s <= d3; d2s <= d2; d1s <= d1; d0s <= d0;
                        count_stop <= count_bin;
                        state <= S_SEND_PREP;
                    end else if (tick) begin
                        // BCD increment (wraps 9999 → 0000)
                        if (d0 == 4'd9) begin
                            d0 <= 4'd0;
                            if (d1 == 4'd9) begin
                                d1 <= 4'd0;
                                if (d2 == 4'd9) begin
                                    d2 <= 4'd0;
                                    d3 <= (d3 == 4'd9) ? 4'd0 : d3 + 4'd1;
                                end else d2 <= d2 + 4'd1;
                            end else d1 <= d1 + 4'd1;
                        end else d0 <= d0 + 4'd1;

                        // Binary increment
                        count_bin <= (count_bin == 14'd9999) ? '0 : count_bin + 14'd1;
                    end
                end

                // ---- SEND_PREP: build TX buffer, fire first byte ----
                S_SEND_PREP: begin
                    send_buf[0] <= 8'h30 + {4'b0, d3s};
                    send_buf[1] <= 8'h30 + {4'b0, d2s};
                    send_buf[2] <= 8'h30 + {4'b0, d1s};
                    send_buf[3] <= 8'h30 + {4'b0, d0s};
                    send_buf[4] <= 8'h0A;   // '\n'

                    // Send first byte (d3 thousands) immediately
                    tx_data_r  <= 8'h30 + {4'b0, d3s};
                    tx_valid_r <= 1'b1;
                    send_idx   <= 3'd1;     // next byte to send on tx_done
                    state      <= S_SENDING;
                end

                // ---- SENDING: send remaining 4 bytes on tx_done ----
                S_SENDING: begin
                    if (tx_done) begin
                        if (send_idx <= 3'd4) begin
                            tx_data_r  <= send_buf[send_idx];
                            tx_valid_r <= 1'b1;
                            send_idx   <= send_idx + 3'd1;
                        end else begin
                            state <= S_DONE;
                        end
                    end
                end

                // ---- DONE: display frozen; KEY[0] resets ----
                S_DONE: begin
                    if (key0_press) state <= S_IDLE;
                end

            endcase
        end
    end

    // ----------------------------------------------------------------
    // UART TX instance
    // ----------------------------------------------------------------
    uart_tx #(
        .CLK_FREQ(50_000_000),
        .BAUD(9600)
    ) u_uart_tx (
        .clk      (clk),
        .rst_n    (rst_n),
        .tx_data  (tx_data_r),
        .tx_valid (tx_valid_r),
        .tx       (fpga_tx_pin),
        .tx_busy  (tx_busy)
    );

    // ----------------------------------------------------------------
    // LED Bar Graph  (more LEDs = closer to 1000)
    // Active only when not idle; uses live or frozen count
    // ----------------------------------------------------------------
    wire [13:0] disp_count;
    wire        show_stop = (state == S_SEND_PREP) |
                            (state == S_SENDING)   |
                            (state == S_DONE);
    assign disp_count = show_stop ? count_stop : count_bin;

    wire [13:0] distance;
    assign distance = (disp_count >= 14'd1000) ? (disp_count - 14'd1000)
                                               : (14'd1000  - disp_count);

    wire led_on = (state != S_IDLE);
    assign LEDR[0] = led_on & (distance <= 14'd460);
    assign LEDR[1] = led_on & (distance <= 14'd410);
    assign LEDR[2] = led_on & (distance <= 14'd360);
    assign LEDR[3] = led_on & (distance <= 14'd310);
    assign LEDR[4] = led_on & (distance <= 14'd260);
    assign LEDR[5] = led_on & (distance <= 14'd210);
    assign LEDR[6] = led_on & (distance <= 14'd160);
    assign LEDR[7] = led_on & (distance <= 14'd110);
    assign LEDR[8] = led_on & (distance <= 14'd60);
    assign LEDR[9] = led_on & (distance <= 14'd10);   // win zone ±10

    // ----------------------------------------------------------------
    // 7-Segment Display
    // ----------------------------------------------------------------
    wire [3:0] disp3 = show_stop ? d3s : d3;
    wire [3:0] disp2 = show_stop ? d2s : d2;
    wire [3:0] disp1 = show_stop ? d1s : d1;
    wire [3:0] disp0 = show_stop ? d0s : d0;

    seven_segment seg3 (.data(disp3), .blank(1'b0), .seg(HEX3));
    seven_segment seg2 (.data(disp2), .blank(1'b0), .seg(HEX2));
    seven_segment seg1 (.data(disp1), .blank(1'b0), .seg(HEX1));
    seven_segment seg0 (.data(disp0), .blank(1'b0), .seg(HEX0));

    assign HEX4 = 8'hFF;   // blank
    assign HEX5 = 8'hFF;   // blank

endmodule
