using System;
using System.Collections.Generic;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.ServiceProcess;
using System.Text;
using System.Threading;
using System.Web.Script.Serialization;
using LibreHardwareMonitor.Hardware;

// Read-only hardware monitoring. No fan control, firmware or remote interface.
public sealed class SensorService : ServiceBase
{
    readonly ManualResetEvent stop = new ManualResetEvent(false);
    readonly object gate = new object();
    Thread polling, server;
    UdpClient udp;
    string snapshot;
    public SensorService() { ServiceName = "COUGARStudioSensors"; AutoLog = true; }

    static object Number(float? value) {
        return value.HasValue && !float.IsNaN(value.Value) && !float.IsInfinity(value.Value)
            ? (object)value.Value : null;
    }
    static object Temperature(float? value) {
        return value.HasValue && value.Value > 0 && value.Value < 150 ? Number(value) : null;
    }
    static IEnumerable<IHardware> Flatten(IEnumerable<IHardware> hardware) {
        foreach (IHardware item in hardware) {
            yield return item;
            foreach (IHardware child in Flatten(item.SubHardware)) yield return child;
        }
    }
    static float? Pick(IEnumerable<ISensor> sensors, SensorType type, string preferred, bool requireName = false) {
        var found = sensors.Where(s => s.SensorType == type && s.Value.HasValue).ToList();
        var named = found.FirstOrDefault(s => s.Name.IndexOf(preferred, StringComparison.OrdinalIgnoreCase) >= 0);
        return named != null ? named.Value : (!requireName && found.Count > 0 ? found[0].Value : null);
    }
    static string Read(Computer computer) {
        var hardware = Flatten(computer.Hardware).ToList();
        foreach (IHardware item in hardware) item.Update();
        var cpu = hardware.Where(h => h.HardwareType == HardwareType.Cpu).SelectMany(h => h.Sensors).ToList();
        var gpu = hardware.Where(h => h.HardwareType == HardwareType.GpuNvidia || h.HardwareType == HardwareType.GpuAmd || h.HardwareType == HardwareType.GpuIntel).FirstOrDefault();
        var gs = gpu == null ? new List<ISensor>() : gpu.Sensors.ToList();
        var all = hardware.SelectMany(h => h.Sensors).ToList();
        object[] values = {
            Temperature(Pick(cpu, SensorType.Temperature, "Package")),
            Number(Pick(all, SensorType.Fan, "CPU", true)),
            Number(Pick(cpu, SensorType.Power, "Package")),
            Number(Pick(cpu, SensorType.Load, "Total")),
            Temperature(Pick(gs, SensorType.Temperature, "Core")),
            Number(Pick(gs, SensorType.Load, "Core"))
        };
        return new JavaScriptSerializer().Serialize(new { values = values, timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(), source = "LibreHardwareMonitor 0.9.6" });
    }
    static Computer OpenComputer() {
        var computer = new Computer { IsCpuEnabled = true, IsGpuEnabled = true, IsMotherboardEnabled = true,
            IsMemoryEnabled = false, IsStorageEnabled = false, IsNetworkEnabled = false, IsControllerEnabled = false };
        computer.Open();
        return computer;
    }
    void Poll() {
        Computer computer = null;
        try {
            computer = OpenComputer();
            while (!stop.WaitOne(0)) {
                try { string result = Read(computer); lock (gate) snapshot = result; }
                catch (Exception error) { lock (gate) snapshot = new JavaScriptSerializer().Serialize(new { error = error.Message, timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds() }); }
                stop.WaitOne(1000);
            }
        } catch (Exception error) {
            lock (gate) snapshot = new JavaScriptSerializer().Serialize(new { error = error.Message, timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds() });
        } finally { if (computer != null) computer.Close(); }
    }
    void Serve() {
        while (!stop.WaitOne(0)) {
            try {
                IPEndPoint peer = new IPEndPoint(IPAddress.Loopback, 0);
                byte[] packet = udp.Receive(ref peer);
                if (!IPAddress.IsLoopback(peer.Address) || Encoding.ASCII.GetString(packet) != "COUGAR-STUDIO/1") continue;
                string reply;
                lock (gate) reply = snapshot ?? "{\"error\":\"Sensores iniciando\"}";
                byte[] bytes = Encoding.UTF8.GetBytes(reply);
                udp.Send(bytes, bytes.Length, peer);
            } catch (SocketException) { if (stop.WaitOne(0)) break; }
              catch (ObjectDisposedException) { break; }
        }
    }
    protected override void OnStart(string[] args) {
        udp = new UdpClient(AddressFamily.InterNetwork);
        udp.ExclusiveAddressUse = true;
        udp.Client.ReceiveTimeout = 1000;
        udp.Client.Bind(new IPEndPoint(IPAddress.Loopback, 8896));
        polling = new Thread(Poll) { IsBackground = true };
        server = new Thread(Serve) { IsBackground = true };
        polling.Start(); server.Start();
    }
    protected override void OnStop() {
        stop.Set();
        if (udp != null) udp.Close();
        if (server != null) server.Join(2000);
        if (polling != null) polling.Join(5000);
    }
    public static int Main(string[] args) {
        if (args.Contains("--once")) {
            try { var computer = OpenComputer(); Thread.Sleep(1000); Console.WriteLine(Read(computer)); computer.Close(); return 0; }
            catch (Exception error) { Console.Error.WriteLine(error.ToString()); return 1; }
        }
        ServiceBase.Run(new SensorService());
        return 0;
    }
}
