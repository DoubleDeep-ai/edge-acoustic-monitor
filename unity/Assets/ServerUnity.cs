using System;
using System.Collections;
using System.Net;
using System.Net.Sockets;
using System.Text;
using UnityEngine;
using UnityEngine.UI;

public class ServerUnity : MonoBehaviour
{
    public int port = 8080;
    public Text receivedText;
    public Text alertText;
    public Button temperatureUpButton;
    public Button temperatureDownButton;
    public Button muteButton;

    private TcpListener server;
    private TcpClient client;
    private NetworkStream stream;
    private readonly byte[] buffer = new byte[1024];

    void Start()
    {
        temperatureUpButton.onClick.AddListener(() => Debug.Log("Temperature up requested"));
        temperatureDownButton.onClick.AddListener(() => Debug.Log("Temperature down requested"));
        muteButton.onClick.AddListener(() => Debug.Log("Mute requested"));
        StartServer();
    }

    void Update()
    {
        if (client == null || !client.Connected || stream == null || !stream.DataAvailable)
        {
            return;
        }

        int bytesRead = stream.Read(buffer, 0, buffer.Length);
        if (bytesRead == 0)
        {
            CloseClient();
            return;
        }

        string message = Encoding.UTF8.GetString(buffer, 0, bytesRead);
        receivedText.text = message;
        alertText.text = message.Contains("ANOMALY")
            ? DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + "  Check this machine"
            : string.Empty;
    }

    void StartServer()
    {
        try
        {
            server = new TcpListener(IPAddress.Any, port);
            server.Start();
            StartCoroutine(AcceptClients());
            Debug.Log("Unity monitor listening on port " + port);
        }
        catch (SocketException error)
        {
            Debug.LogError("Could not start Unity monitor: " + error.Message);
        }
    }

    IEnumerator AcceptClients()
    {
        while (server != null)
        {
            if (server.Pending())
            {
                CloseClient();
                client = server.AcceptTcpClient();
                stream = client.GetStream();
                Debug.Log("Device connected: " + client.Client.RemoteEndPoint);
            }
            yield return null;
        }
    }

    void CloseClient()
    {
        stream?.Close();
        client?.Close();
        stream = null;
        client = null;
    }

    void OnDestroy()
    {
        CloseClient();
        server?.Stop();
        server = null;
    }
}
