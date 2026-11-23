using System;
using UnityEngine;
using UnityEngine.UI;

public class Temp : MonoBehaviour
{
    public Text temperatureText;
    public Text soundText;  // 변수명 수정
    public Text highTemperatureText;
    public Text soundhighText;  // 변수명 수정

    void Start()
    {
        // 시작 시 한번 온도 업데이트
        UpdateTemperature();
        // 1초마다 UpdateTemperature 함수 호출
        InvokeRepeating("UpdateTemperature", 1f, 1f);
    }

    void UpdateTemperature()
    {
        // 18에서 20 사이의 랜덤한 온도값 및 소리값 생성 (UnityEngine.Random 사용)
        float randomTemperature = UnityEngine.Random.Range(20f, 23f);
        float randomSound = UnityEngine.Random.Range(60f, 75f);

        // 소수점 둘째 자리까지 표시
        string formattedTemperature = randomTemperature.ToString("F1");
        string formattedSound = randomSound.ToString("F1");  // 변수명 수정

        // 텍스트 업데이트
        temperatureText.text = formattedTemperature + " ℃";
        soundText.text = formattedSound + " dB ";

        // 온도가 21도를 넘어가면 다른 코드로 처리
        if (randomTemperature > 21f)
        {
            HandleTemperatureAbove21(randomTemperature);
        }

        // 소리가 68dB를 넘어가면 다른 코드로 처리
        if (randomSound > 68f)
        {
            HandleSoundAbove70(randomSound);
        }
    }

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
        string formattedSound = sound.ToString("F1");  // 변수명 수정
        string formattedTime = currentTime.ToString("yyyy-MM-dd HH:mm:ss");
        soundhighText.text = formattedTime + " 소리가 " + formattedSound + " dB 를 넘어갑니다. ";
    }
}
