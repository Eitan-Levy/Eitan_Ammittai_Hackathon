// UART Transmitter -- 9600 baud, 50 MHz clock, 8N1
// Accepts one byte per transmission.
// tx_valid: one-cycle pulse to start; tx_data must be stable on that cycle.
// tx_busy: combinationally high while a byte is in flight.

module uart_tx #(
    parameter CLK_FREQ = 50_000_000,
    parameter BAUD     = 9600
)(
    input  logic       clk,
    input  logic       rst_n,
    input  logic [7:0] tx_data,
    input  logic       tx_valid,   // one-cycle pulse to start transmission
    output logic       tx,         // serial output (idle = 1)
    output logic       tx_busy     // high while transmitting
);

    localparam CLKS_PER_BIT = CLK_FREQ / BAUD;  // 5208

    typedef enum logic [1:0] {
        TX_IDLE, TX_START, TX_DATA, TX_STOP
    } state_t;

    state_t      state;
    logic [15:0] clk_cnt;
    logic [2:0]  bit_idx;
    logic [7:0]  shift_reg;

    // tx_busy is combinational — high whenever we are not idle
    assign tx_busy = (state != TX_IDLE);

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state     <= TX_IDLE;
            tx        <= 1'b1;
            clk_cnt   <= '0;
            bit_idx   <= '0;
            shift_reg <= '0;
        end else begin
            case (state)
                TX_IDLE: begin
                    tx <= 1'b1;
                    if (tx_valid) begin
                        shift_reg <= tx_data;
                        clk_cnt   <= '0;
                        bit_idx   <= '0;
                        state     <= TX_START;
                    end
                end

                TX_START: begin
                    tx <= 1'b0;  // start bit
                    if (clk_cnt == CLKS_PER_BIT - 1) begin
                        clk_cnt <= '0;
                        state   <= TX_DATA;
                    end else
                        clk_cnt <= clk_cnt + 1;
                end

                TX_DATA: begin
                    tx <= shift_reg[bit_idx];  // LSB first
                    if (clk_cnt == CLKS_PER_BIT - 1) begin
                        clk_cnt <= '0;
                        if (bit_idx == 3'd7)
                            state <= TX_STOP;
                        else
                            bit_idx <= bit_idx + 1;
                    end else
                        clk_cnt <= clk_cnt + 1;
                end

                TX_STOP: begin
                    tx <= 1'b1;  // stop bit
                    if (clk_cnt == CLKS_PER_BIT - 1) begin
                        clk_cnt <= '0;
                        state   <= TX_IDLE;
                    end else
                        clk_cnt <= clk_cnt + 1;
                end
            endcase
        end
    end

endmodule
