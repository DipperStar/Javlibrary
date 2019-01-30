# Javlibrary
-----------------------------------
Javlibrary爬虫 for Python3，该项目可以实现以下功能:
* 获取最高评分/最受期待榜的作品
* 获取所有演员名及其作品目录地址
* 获取指定演员所有作品
* 获取指定番号磁力链接
* 输出内容到excel

## 安装一下
---------------------------------
### 需要安装以下包
  ```Python
  pip install requests
  pip install BeautifulSoup
  pip install pandas
  pip install selenium
  pip install pymongo
  pip install retrying
  ```
### 依赖[chrome驱动](http://blog.csdn.net/guodongxiaren "chrome驱动下载")，各驱动对应chrome版本号如下：
* ChromeDriver v2.45 (2018-12-10)----------Supports Chrome v70-72
* ChromeDriver v2.44 (2018-11-19)----------Supports Chrome v69-71
* ChromeDriver v2.43 (2018-10-16)----------Supports Chrome v69-71

## 怎么开始
----------------------------------
### 以下例子完成查找指定演员所有影片及磁力链接的操作：
  ```Python
  if __name__ == '__main__':
    jav = JavLib()
    jav.girlindex('初川みなみ')
  ```

## 方法说明
--------------------------
|方法|功能|参数|
| :----------: | :-----------:|:-----------:|
| rank   | 获取最高评分/最受期待榜的作品及磁力链接  | mode排行榜种类 |
| girlindex   |  获取指定演员所有作品及磁力链接  | girl演员名 |
| allgirls   |  更新所有演员名及地址  | NULL |
| torrent   |  获取指定番号磁力链接   | identity番号 |
| write_down   |  输出内容到excel   | datas数据, filename文件名 |

## 举个栗子
----------------------------
* 获取最高评分/最受期待榜的作品及磁力链接
```Python
jav = JavLib(mode = 'mostwanted') # mode 默认为bestrated
jav.rank()
jav.rankdb().find(select) # 从rankdb输出
```
* 获取指定演员所有作品及磁力链接
```Python
jav.girlindex('初川みなみ')
jav.rankdb().find(select) # 从rankdb输出
```
* 更新演员名录
```Python
jav.allgirls()
jav.girlsindexdb ().find(select) # 从rankdb输出
```
* 获取指定番号磁力链接
```Python
indentity = 'SSNI-266'
list_torrent = jav.torrent(indentity)[indentity] # 获得list(dict)结构数据
jav.write_down(list_torrent, identity) # 输出到identity.xlsx
```

## 数据库
-------------------------------------------
### 本项目使用MongoDB作为数据库：
* MongoDB('Javdb', 'girlsname')  # 所有girl名称—>页面编码键值对
* MongoDB('Javdb', 'rankdb')  # 最高评分/最受期待榜
* MongoDB('Javdb', 'girlsindexdb')  # 单个girl的作品db
