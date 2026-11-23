using System;
using System.Collections;
using System.Diagnostics;
using System.Net;
using System.Net.Sockets;
using System.Text;
using UnityEngine;
using UnityEngine.UI;
using static System.Net.Mime.MediaTypeNames;

public class SeverUnity : MonoBehaviour
{
    TcpListener server;
    TcpClient client;
    NetworkStream stream;
    byte[] buffer = new byte[1024];

    public int port = 8080;
    public Text receivedText1;
    public Text receivedText2;
    public Button TempUPButton;
    public Button TempDownButton;
    public Button MuteButton;

    // 추가된 변수
    private float temperatureValue = 0f;
    private float soundValue = 0f;

    public Text highTemperatureText; // 추가된 부분
    public Text soundhighText; // 추가된 부분

    void Start()
    {
        StartServer();
        // 각 버튼에 대한 클릭 이벤트를 각각의 함수와 연결
        TempUPButton.onClick.AddListener(OnTempUPButtonClick);
        TempDownButton.onClick.AddListener(OnTempDownButtonClick);
        MuteButton.onClick.AddListener(OnMuteButtonClick);
    }

    void Update()
    {
        if (client != null && client.Connected)
        {
            if (stream.DataAvailable)
            {
                int bytesRead = stream.Read(buffer, 0, buffer.Length);
                string receivedMessage = Encoding.ASCII.GetString(buffer, 0, bytesRead);
                Debug.Log("Received from Unity: " + receivedMessage);

                // 값을 받아온 문자열을 실수로 변환
                if (float.TryParse(receivedMessage, out float value))
                {
                    // 온도 및 소리 값 업데이트
                    temperatureValue = value;
                    soundValue = value;

                    // 온도가 21도를 넘어가면 다른 코드로 처리
                    if (temperatureValue > 21f)
                    {
                        HandleTemperatureAbove21(temperatureValue);
                    }

                    // 소리가 68dB를 넘어가면 다른 코드로 처리
                    if (soundValue > 68f)
                    {
                        HandleSoundAbove70(soundValue);
                    }
                }

                if (receivedText1 != null)
                {
                    receivedText1.text = "Temperature : " + temperatureValue.ToString();
                    receivedText2.text = "Sound : " + soundValue.ToString();
                }
            }
        }
    }

    void StartServer()
    {
        try
        {
            server = new TcpListener(IPAddress.Any, port);
            server.Start();

            Debug.Log("Server is listening on port " + port);

            StartCoroutine(AcceptClients());
        }
        catch (Exception e)
        {
            Debug.LogError("Error starting the server: " + e.Message);
        }
    }

    IEnumerator AcceptClients()
    {
        while (true)
        {
            yield return null;

            if (server.Pending())
            {
                client = server.AcceptTcpClient();
                stream = client.GetStream();
                Debug.Log("Client connected: " + ((IPEndPoint)client.Client.RemoteEndPoint).Address);
            }
        }
    }

    void OnDestroy()
    {
        if (server != null)
        {
            server.Stop();
        }

        if (client != null)
        {
            client.Close();
        }
    }

    // 각 버튼에 대한 클릭 콜백 함수 정의
    void OnTempUPButtonClick()
    {
        Debug.Log("TempUPButton Clicked!");
        // TempUPButton이 클릭되었을 때 실행할 코드를 추가할 수 있습니다.
    }

    void OnTempDownButtonClick()
    {
        Debug.Log("TempDownButton Clicked!");
        // TempDownButton이 클릭되었을 때 실행할 코드를 추가할 수 있습니다.
    }

    void OnMuteButtonClick()
    {
        Debug.Log("MuteButton Clicked!");
        // MuteButton이 클릭되었을 때 실행할 코드를 추가할 수 있습니다.
    }

    // 추가된 함수
    void HandleTemperatureAbove21(float temperature)
    {
        // 여기에 21도를 넘어가는 온도를 처리하는 코드
        DateTime currentTime = DateTime.Now;
        string formattedTime = currentTime.ToString("yyyy-MM-dd HH:mm:ss");
        string formattedTemp = temperature.ToString("F1");
        highTemperatureText.text = formattedTime + " 온도가 " + formattedTemp + " ℃ 를 넘어갑니다. ";
    }

    void HandleSoundAbove70(float sound)
    {
        // 여기에 70dB를 넘어가는 소리를 처리하는 코드
        DateTime currentTime = DateTime.Now;
        string formattedSound = sound.ToString("F1");
        string formattedTime = currentTime.ToString("yyyy-MM-dd HH:mm:ss");
        soundhighText.text = formattedTime + " 소리가 " + formattedSound + " dB 를 넘어갑니다. ";
    }
}
