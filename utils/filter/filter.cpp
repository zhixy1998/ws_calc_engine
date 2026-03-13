/// <summary>
///SG滤波
/// </summary>
/// <param name="m">半步宽m>0,m越大，平滑度越高)</param>
void SetCoefficient(int m)
{
    Coefficient.clear();
    int w = m * 2 + 1;
    double W2 = pow(w, 2);
    double a1 = 15 / (W2 - 4);
    double a2 = (W2 - 1) / 12;
    for (int j = -m; j <= m; j++)
    {
        Coefficient.push_back((1 + a1 * (a2 - pow(j, 2))) / w);
    }

}
/// <summary>
/// 单点SG平滑
/// </summary>
/// <param name="list">平滑参考点(list.Length 必须等于 this.Coefficient.Length)</param>
/// <returns></returns>
float SGSmooth(std::deque<float> list)
{
    if(list.size() != Coefficient.size())
        return list[list.size()-1];

    double result = 0;
    for (int i = 0; i < Coefficient.size(); i++)
    {
        result += Coefficient[i] * list[i];
    }
    return result;
}
//滑动平均滤波
float ApplySildeFilter(std::deque<float> data, int windowSize, int numIterations)
{
    std::deque<float> filteredData(data.begin(), data.end());
    int startIndex = 0;
    int endIndex = filteredData.size() - 1;
    int count = endIndex - startIndex + 1;
    double sum = 0;
    std::deque<float>  tempData;
    for (int iteration = 0; iteration < numIterations; iteration++)
    {
        tempData.clear();
        for (int i = 0; i < filteredData.size(); i++)
        {
                startIndex = max(0, i - windowSize / 2);
                endIndex = min(filteredData.size() - 1, i + windowSize / 2);
                count = endIndex - startIndex + 1;
                sum = std::accumulate(filteredData.begin()+startIndex, filteredData.begin()+startIndex+count, 0.0000f);
                tempData.push_back(sum/count);
        }
        filteredData = tempData;
    }
    return std::accumulate(filteredData.begin()+10, filteredData.end(), 0.0000f) / (filteredData.size()-10);
}

//中位平均滤波
float MidFilter(std::deque<float> inputList)
{
     std::deque<float> window(inputList.begin(), inputList.end());
     std::sort(window.begin(), window.end());
     float output = std::accumulate(window.begin()+1, window.end()-1, 0.0000f)/(window.size()-2);

     return output;
}