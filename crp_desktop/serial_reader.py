
import time
import sqlite3
import serial
from crp_desktop.resources import READ_TIMEOUT, BUFFER_RESET_TIMEOUT, BAUD_RATES, DB_PATH
from crp_desktop.parser import extract_fields_from_block
from crp_desktop.db import save_result, get_db
from crp_desktop import signals as signals_mod

def connect_port_specific(port_name: str, baud: int):
    try:
        ser = serial.Serial(port_name, baudrate=baud, timeout=READ_TIMEOUT)
        return ser, f"Connected to {port_name} @ {baud}"
    except Exception as e:
        return None, f"Could not open {port_name} @ {baud}: {e}"

def read_serial_and_store_results(stop_event, port_name: str, baud: int):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    ser, msg = connect_port_specific(port_name, baud)
    if ser is None:
        if signals_mod.signals:
            signals_mod.signals.status.emit("Serial: " + msg)
        conn.close()
        return
    if signals_mod.signals:
        signals_mod.signals.status.emit("Serial: " + msg)
    buffer = ""
    last_read_time = time.time()
    try:
        while not stop_event.is_set():
            try:
                n = ser.in_waiting
            except Exception:
                n = 0
            if n:
                raw = ser.read(n)
                try:
                    text = raw.decode('latin1', errors='ignore')
                except Exception:
                    text = raw.decode('utf-8', errors='ignore')
                buffer += text
                last_read_time = time.time()

                while True:
                    stx_idx = buffer.find('\x02')
                    etx_idx = buffer.find('\x03')
                    if stx_idx != -1 and etx_idx != -1 and etx_idx > stx_idx:
                        packet = buffer[stx_idx + 1:etx_idx]
                        parsed = extract_fields_from_block(packet)
                        try:
                            save_result(parsed, conn)
                            if signals_mod.signals:
                                signals_mod.signals.new_result.emit(parsed)
                                signals_mod.signals.status.emit("Saved new result: " + parsed.get("ID", "<no id>"))
                        except Exception as e:
                            if signals_mod.signals:
                                signals_mod.signals.status.emit("DB save error: " + str(e))
                        buffer = buffer[etx_idx + 1:]
                        continue
                    if '\n$FE' in buffer or ' CRP' in buffer:
                        last_nl = max(buffer.rfind('\n'), buffer.rfind('\r\n'))
                        if last_nl > 0:
                            packet = buffer[:last_nl + 1]
                            parsed = extract_fields_from_block(packet)
                            try:
                                save_result(parsed, conn)
                                if signals_mod.signals:
                                    signals_mod.signals.new_result.emit(parsed)
                                    signals_mod.signals.status.emit("Saved new result: " + parsed.get("ID", "<no id>"))
                            except Exception as e:
                                if signals_mod.signals:
                                    signals_mod.signals.status.emit("DB save error: " + str(e))
                            buffer = buffer[last_nl + 1:]
                            continue
                    break
            else:
                if buffer and (time.time() - last_read_time) > BUFFER_RESET_TIMEOUT:
                    parsed = extract_fields_from_block(buffer)
                    try:
                        save_result(parsed, conn)
                        if signals_mod.signals:
                            signals_mod.signals.new_result.emit(parsed)
                            signals_mod.signals.status.emit("Saved new result: " + parsed.get("ID", "<no id>"))
                    except Exception as e:
                        if signals_mod.signals:
                            signals_mod.signals.status.emit("DB save error: " + str(e))
                    buffer = ""
                time.sleep(0.08)
    except Exception as e:
        if signals_mod.signals:
            signals_mod.signals.status.emit("Serial listener error: " + str(e))
    finally:
        try:
            ser.close()
        except Exception:
            pass
        conn.close()
        if signals_mod.signals:
            signals_mod.signals.status.emit("Serial listener stopped")
