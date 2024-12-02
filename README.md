# **Тестовое задание Dr.Web**

Для запуска проекта необходимо выполнить `docker-compose up -d`

## Создание задачи

Запрос на создание задачи `curl -X POST http://127.0.0.1:8000/tasks -H "Content-Type: application/json"`

Пример ответа:

```json
{
	"message": "Task created successfully",
	"task_id": "74e9375011b248c892c277ec1c48dd1e"
}
```

## Получение статуса задачи

Запрос на получение статуса задачи `curl -X GET http://127.0.0.1:8000/tasks/74e9375011b248c892c277ec1c48dd1e -H "Content-Type: application/json"`

Пример ответа:

```json
{
	"status": "Completed",
	"create_time": "2024-12-02T21:58:55.347065Z",
	"start_time": "2024-12-02T21:58:55.348817Z",
	"time_to_execute": 9
}
```
